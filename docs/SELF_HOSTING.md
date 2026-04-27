# Self-hosting `ai-music` với Docker Compose + Cloudflare Tunnel

Hướng dẫn chạy toàn bộ stack (backend FastAPI + frontend Next.js) trên server
của bạn và mở ra Internet bằng [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
ở chế độ **token** — không cần mở port, không cần public IP.

> Mọi thứ chạy bằng `docker compose up`. Bạn chỉ cần Docker và một tài khoản
> Cloudflare (miễn phí cũng được) gắn với một domain.

---

## 1. Yêu cầu

- Docker Engine **24+** và Docker Compose **v2** (`docker compose ...`).
- Một domain đang dùng Cloudflare DNS.
- Một LLM API key tương thích OpenAI (OpenAI, Together, vLLM, Ollama, …).

---

## 2. Tạo Cloudflare Tunnel và lấy token

1. Vào [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com) →
   **Networks → Tunnels → Create a tunnel**.
2. Chọn **Cloudflared**, đặt tên (ví dụ `ai-music`).
3. Ở bước "Install and run a connector", chọn tab **Docker** — Cloudflare sẽ
   hiển thị một câu lệnh dạng:

   ```
   docker run cloudflare/cloudflared:latest tunnel --no-autoupdate run --token eyJhIjoi...
   ```

   **Copy phần token** (`eyJhIjoi...`). Đó chính là `TUNNEL_TOKEN`.

4. Sang tab **Public Hostnames** trong cùng tunnel, thêm hai hostname:

   | Subdomain | Domain | Service |
   | --- | --- | --- |
   | `music` | `example.com` | `HTTP://frontend:3000` |
   | `api` | `example.com` | `HTTP://backend:8000` |

   Tên service phải khớp **chính xác** với tên service trong
   `docker-compose.yml` (`frontend`, `backend`) vì cloudflared kết nối qua
   network nội bộ của compose. Cloudflare sẽ tự tạo bản ghi DNS CNAME ở zone
   của bạn.

---

## 3. Cấu hình `.env`

```bash
cp .env.example .env
```

Mở `.env` và điền:

```dotenv
# Cloudflare Tunnel
TUNNEL_TOKEN=eyJhIjoi...      # token bạn vừa copy

# URL công khai mà BROWSER dùng để gọi backend (đổi theo domain của bạn)
PUBLIC_API_BASE=https://api.example.com

# CORS — thêm hostname public của frontend
CORS_ORIGINS=https://music.example.com

# LLM — chọn 1 trong 2 cách
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

> `PUBLIC_API_BASE` được **bake vào bundle Next.js lúc build**. Nếu sau này bạn
> đổi domain backend, phải chạy lại `docker compose build frontend`.

---

## 4. Build và chạy

```bash
docker compose up -d --build
```

Lần đầu sẽ build hai image (`ai-music-backend`, `ai-music-frontend`) và pull
`cloudflare/cloudflared`. Mất khoảng 2–5 phút.

Kiểm tra:

```bash
docker compose ps
docker compose logs -f cloudflared    # xem tunnel đã connect chưa
docker compose logs -f backend
```

Khi cloudflared báo `Registered tunnel connection` ở 4 region, mở:

- Frontend: `https://music.example.com`
- Backend health: `https://api.example.com/health` → `{"status":"ok"}`
- API docs: `https://api.example.com/docs`

---

## 5. Vận hành

| Việc | Lệnh |
| --- | --- |
| Cập nhật code | `git pull && docker compose up -d --build` |
| Xem log | `docker compose logs -f [service]` |
| Restart 1 service | `docker compose restart backend` |
| Tắt | `docker compose down` |
| Tắt + xoá volume | `docker compose down -v` (mất drafts đã lưu) |

Drafts/sessions của Studio được lưu trong volume `backend-data`
(`/app/backend/app/data` trong container). Backup bằng:

```bash
docker run --rm -v ai-music_backend-data:/data -v $PWD:/backup alpine \
  tar czf /backup/ai-music-data-$(date +%F).tgz -C /data .
```

---

## 6. Bảo mật / chỉ phục vụ qua tunnel

Mặc định `docker-compose.yml` có map port `3000` và `8000` ra host (tiện cho
debug LAN). Trong môi trường production thuần tunnel, bỏ block `ports:` của
`backend` và `frontend` — cloudflared vẫn truy cập được qua network nội bộ.

`.env` không được commit. `TUNNEL_TOKEN` cũng đừng paste vào chat/issue —
nếu lộ, **revoke tunnel** trong Zero Trust dashboard và tạo lại.

---

## 7. Troubleshooting

- **Frontend gọi sai API URL** → bạn quên `docker compose build frontend` sau
  khi đổi `PUBLIC_API_BASE`.
- **CORS error trong console browser** → thêm hostname frontend vào
  `CORS_ORIGINS` rồi `docker compose up -d backend`.
- **Cloudflare báo `502 Bad Gateway`** → service tên trong Public Hostname
  phải là `http://backend:8000` / `http://frontend:3000` (đúng tên container
  trong compose), không phải `localhost`.
- **Backend không thấy LLM key** → `docker compose exec backend env | grep LLM`
  để xác nhận biến đã được inject.
