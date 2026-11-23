"""라온 자체 모델(GPT-2 medium 355M, instruction-tuned) OpenAI 호환 로컬 서버.

릴리스 raon-llm-v1 의 gpt2-medium355M-sft.pth(state_dict)를 로드해 127.0.0.1에서
POST /v1/chat/completions 를 제공한다. 게임 라온 어댑터(raon_llm.py)와 호환:
system+user 메시지·max_tokens·temperature 를 받아 Alpaca 프롬프트로 생성.

로컬 전용·학습용. torch + tiktoken 필요.
"""
import argparse
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import tiktoken
import torch
import torch.nn as nn

CFG = {"vocab_size": 50257, "context_length": 1024, "emb_dim": 1024,
       "n_heads": 16, "n_layers": 24, "drop_rate": 0.0, "qkv_bias": True}
EOT = 50256  # <|endoftext|>


class LayerNorm(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.eps = 1e-5
        self.scale = nn.Parameter(torch.ones(dim))
        self.shift = nn.Parameter(torch.zeros(dim))

    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        var = x.var(-1, keepdim=True, unbiased=False)
        return self.scale * (x - mean) / torch.sqrt(var + self.eps) + self.shift


class GELU(nn.Module):
    def forward(self, x):
        return 0.5 * x * (1 + torch.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x ** 3)))


class FeedForward(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(cfg["emb_dim"], 4 * cfg["emb_dim"]),
            GELU(),
            nn.Linear(4 * cfg["emb_dim"], cfg["emb_dim"]),
        )

    def forward(self, x):
        return self.layers(x)


class MultiHeadAttention(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        d = cfg["emb_dim"]
        self.n_heads = cfg["n_heads"]
        self.head_dim = d // cfg["n_heads"]
        self.d_out = d
        self.W_query = nn.Linear(d, d, bias=cfg["qkv_bias"])
        self.W_key = nn.Linear(d, d, bias=cfg["qkv_bias"])
        self.W_value = nn.Linear(d, d, bias=cfg["qkv_bias"])
        self.out_proj = nn.Linear(d, d)
        self.dropout = nn.Dropout(cfg["drop_rate"])
        self.register_buffer("mask", torch.triu(torch.ones(cfg["context_length"], cfg["context_length"]), diagonal=1))

    def forward(self, x):
        b, n, _ = x.shape
        q = self.W_query(x).view(b, n, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.W_key(x).view(b, n, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.W_value(x).view(b, n, self.n_heads, self.head_dim).transpose(1, 2)
        attn = q @ k.transpose(2, 3)
        attn = attn.masked_fill(self.mask.bool()[:n, :n], -torch.inf)
        attn = torch.softmax(attn / k.shape[-1] ** 0.5, dim=-1)
        attn = self.dropout(attn)
        ctx = (attn @ v).transpose(1, 2).contiguous().view(b, n, self.d_out)
        return self.out_proj(ctx)


class TransformerBlock(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.att = MultiHeadAttention(cfg)
        self.ff = FeedForward(cfg)
        self.norm1 = LayerNorm(cfg["emb_dim"])
        self.norm2 = LayerNorm(cfg["emb_dim"])
        self.drop = nn.Dropout(cfg["drop_rate"])

    def forward(self, x):
        x = x + self.drop(self.att(self.norm1(x)))
        x = x + self.drop(self.ff(self.norm2(x)))
        return x


class GPTModel(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.tok_emb = nn.Embedding(cfg["vocab_size"], cfg["emb_dim"])
        self.pos_emb = nn.Embedding(cfg["context_length"], cfg["emb_dim"])
        self.drop_emb = nn.Dropout(cfg["drop_rate"])
        self.trf_blocks = nn.Sequential(*[TransformerBlock(cfg) for _ in range(cfg["n_layers"])])
        self.final_norm = LayerNorm(cfg["emb_dim"])
        self.out_head = nn.Linear(cfg["emb_dim"], cfg["vocab_size"], bias=False)

    def forward(self, idx):
        b, n = idx.shape
        x = self.tok_emb(idx) + self.pos_emb(torch.arange(n, device=idx.device))
        x = self.drop_emb(x)
        x = self.trf_blocks(x)
        x = self.final_norm(x)
        return self.out_head(x)


ENC = tiktoken.get_encoding("gpt2")


def build_prompt(messages):
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    user = next((m["content"] for m in messages if m.get("role") == "user"), "")
    instr = (system + "\n\n" + user).strip() if system else (user or "")
    return ("Below is an instruction that describes a task. "
            "Write a response that appropriately completes the request.\n\n"
            f"### Instruction:\n{instr}\n\n### Response:\n")


@torch.no_grad()
def generate(model, prompt, max_new, temp, top_k=40):
    ids = ENC.encode(prompt)[-(CFG["context_length"] - max_new):]
    idx = torch.tensor([ids], dtype=torch.long)
    for _ in range(max_new):
        logits = model(idx[:, -CFG["context_length"]:])[:, -1, :]
        if top_k:
            v, _ = torch.topk(logits, top_k)
            logits = torch.where(logits < v[:, [-1]], torch.tensor(-float("inf")), logits)
        if temp and temp > 0:
            nxt = torch.multinomial(torch.softmax(logits / temp, dim=-1), 1)
        else:
            nxt = torch.argmax(logits, dim=-1, keepdim=True)
        if int(nxt) == EOT:
            break
        idx = torch.cat([idx, nxt], dim=1)
    out = ENC.decode(idx[0, len(ids):].tolist())
    return out.split("###")[0].strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self._send(404, {"error": {"message": "unknown endpoint"}})
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            messages = req.get("messages") or []
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages required")
            max_tokens = min(int(req.get("max_tokens", 64)), 96)
            temp = float(req.get("temperature", 0.7))
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            return self._send(400, {"error": {"message": str(e)}})
        try:
            text = generate(self.server.model, build_prompt(messages), max_tokens, temp)
            if not text:
                raise ValueError("empty output")
        except Exception as e:  # noqa: BLE001
            return self._send(500, {"error": {"message": f"generation failed: {e}"}})
        self._send(200, {"model": req.get("model", "local-gpt2"),
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": text}}]})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--weights", required=True, help="gpt2-medium355M-sft.pth 경로")
    ap.add_argument("--port", type=int, default=8910)
    ap.add_argument("--threads", type=int, default=1)
    args = ap.parse_args()
    torch.set_num_threads(max(1, args.threads))
    print(f"모델 로드 중: {args.weights}", flush=True)
    model = GPTModel(CFG)
    state = torch.load(args.weights, map_location="cpu")
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    model.load_state_dict(state)
    model.eval()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    srv.model = model
    print(f"라온 자체 모델 준비 완료: http://127.0.0.1:{args.port}/v1/chat/completions (model=local-gpt2)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료")


if __name__ == "__main__":
    main()
