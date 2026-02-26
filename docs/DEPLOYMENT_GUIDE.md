# 🚀 Deployment Guide - Production Ready

**Status**: Passo 4 implementado. Sistema pronto para testes e deployment.

---

## 📋 Pre-Deployment Checklist

### Database
- [x] PostgreSQL configurado e rodando (port 5432)
- [x] Banco "hotel" criado
- [x] Alembic migrations versioned (5fa085db2e97)
- [x] Hotel example seeded
- [ ] Backup strategy defined
- [ ] Authentication configured (se aplicável)

### API
- [x] FastAPI app criado (app/main.py)
- [x] WhatsApp webhook endpoint (/webhook/whatsapp)
- [x] Dependencies wired (HotelContextService, etc)
- [ ] HTTPS configured
- [ ] Rate limiting added
- [ ] CORS configured

### AI Service
- [x] OpenAI API integration ready
- [ ] API key securely stored in .env
- [ ] Token usage monitored
- [ ] Fallback handling tested

### Environment
- [x] .env template provided
- [x] Python dependencies (requirements.txt)
- [x] Alembic configured
- [ ] Docker setup (optional, for containerization)

---

## 🔧 Local Testing (Before Deployment)

### 1. Prepare Environment
```bash
cd hotel-automation

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows

# Verify dependencies
pip list | grep -E "fastapi|sqlalchemy|alembic|openai"
```

### 2. Configure .env
```bash
# Copy template
cp .env.example .env

# Edit with your credentials:
# - DATABASE_URL=postgresql://user:password@localhost:5432/hotel
# - OPENAI_API_KEY=sk-...
# - TWILIO_ACCOUNT_SID=AC...
# - TWILIO_AUTH_TOKEN=...
# - REDIS_URL=redis://localhost:6379
```

### 3. Database Setup
```bash
# Apply migrations to PostgreSQL
alembic upgrade head

# Seed hotel data
python seed_hotel.py

# Verify tables
psql hotel -c "\dt"
```

### 4. Start Server
```bash
# Local development (auto-reload)
python -m uvicorn app.main:app --reload --port 8000

# Production (single worker)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 5. Test Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Test webhook (POST)
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "from": "558133334444",
      "text": {
        "body": "Qual é o horário de check-in?"
      }
    }]
  }'
```

### 6. Validate Context Injection
```bash
# Run test
python test_dual_context.py

# Expected output:
# ======================================================================
# CONTEXTO DO HOTEL (Passo 4):
# ======================================================================
# CONTEXTO DO HOTEL:
# - Nome: Hotel Automation
# - Endereco: Avenida Central, 123, Brasilia - DF
# ...
```

### 7. End-to-End WhatsApp Test (Sandbox)
```
1. Send WhatsApp to Twilio sandbox: +1 415-523-8886
   Message: "join [sandbox-code]"

2. Verify in Twilio console that you're registered

3. Send test message: "Qual é o horário de check-in?"

4. Check server logs for successful processing

5. Verify response received in WhatsApp
   Expected: AI response mentioning "14:00" from hotel context
```

---

## 🐳 Docker Deployment (Optional)

### Dockerfile (Provided)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build & Run
```bash
# Build image
docker build -t hotel-automation:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/hotel" \
  -e OPENAI_API_KEY="sk-..." \
  --name hotel-api \
  hotel-automation:latest
```

### Docker Compose
```bash
# Start all services (API + DB + Redis)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

---

## 🌐 Cloud Deployment (AWS/Azure/GCP)

### AWS EC2 Steps
1. **Launch EC2 instance**
   - OS: Ubuntu 22.04 LTS
   - Type: t3.medium (1GB RAM minimum)
   - Security Group: Allow 80, 443, 8000

2. **Install dependencies**
   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3-pip postgresql
   ```

3. **Clone repo and setup**
   ```bash
   git clone <repo> /opt/hotel-automation
   cd /opt/hotel-automation
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   sudo nano /opt/hotel-automation/.env
   # Add secrets securely (use AWS Secrets Manager)
   ```

5. **Run migrations**
   ```bash
   alembic upgrade head
   python seed_hotel.py
   ```

6. **Start with Gunicorn (persistent)**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app.main:app --timeout 60
   ```

7. **Setup systemd service**
   ```bash
   sudo nano /etc/systemd/system/hotel-api.service
   
   [Unit]
   Description=Hotel Automation API
   After=network.target
   
   [Service]
   User=ubuntu
   WorkingDirectory=/opt/hotel-automation
   Environment="PATH=/opt/hotel-automation/.venv/bin"
   ExecStart=/opt/hotel-automation/.venv/bin/gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   
   # Enable and start
   sudo systemctl enable hotel-api
   sudo systemctl start hotel-api
   ```

8. **Setup reverse proxy (Nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

---

## 🔐 Security Checklist

- [ ] .env file NOT committed to git (add to .gitignore)
- [ ] API keys stored in environment variables or AWS Secrets Manager
- [ ] Database password not hardcoded
- [ ] HTTPS enabled on all endpoints
- [ ] CORS properly configured (whitelist Twilio IPs)
- [ ] Rate limiting implemented
- [ ] Input validation on webhook
- [ ] Logging sanitized (no secrets logged)
- [ ] Regular backups of PostgreSQL

---

## 📊 Monitoring & Logging

### Enable Logging
```python
# app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Monitor Key Metrics
- API response time (should be <2s for AI calls)
- Database query time (should be <200ms for context queries)
- Webhook failures (rate, reasons)
- AI API usage (tokens, costs)
- Queue depth (if using background jobs)

### Log Management
```bash
# View logs (local)
tail -f /var/log/hotel-api.log

# Or with systemd
journalctl -u hotel-api -f

# Archive logs
find /var/log -name "*.log" -mtime +30 -delete
```

---

## 🔄 Database Migrations in Production

### Before Deploying New Code
```bash
# Generate migration from models
alembic revision --autogenerate -m "add_new_field"

# Review migration
cat alembic/versions/[hash]_add_new_field.py

# Test locally
alembic upgrade head
# Test app...
alembic downgrade -1

# Commit to git
git add alembic/versions/
git commit -m "Migration: add_new_field"
```

### Deployment Process
```bash
# 1. Pull latest code
git pull origin main

# 2. Apply migrations
alembic upgrade head

# 3. Restart API
systemctl restart hotel-api

# 4. Verify
curl https://your-domain.com/health
```

### Rollback if Needed
```bash
# View history
alembic history

# Downgrade to previous version
alembic downgrade -1

# Or specific version
alembic downgrade [specific_revision_id]
```

---

## 🧪 Test Cases for Production

### Functional Tests
```bash
# Test hotel context retrieval
python -c "
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.hotel_repository_sql import HotelRepositorySQL
from app.application.services.hotel_context_service import HotelContextService

session = SessionLocal()
repo = HotelRepositorySQL(session)
service = HotelContextService(repo)
ctx = service.get_context()
assert 'Hotel Automation' in ctx, 'Hotel context missing'
print('✓ Hotel context test passed')
"

# Test database connection
python -c "
from app.infrastructure.persistence.sql.database import SessionLocal
db = SessionLocal()
result = db.execute('SELECT 1').first()
assert result, 'DB connection failed'
print('✓ Database connection test passed')
"

# Test AI integration
python -c "
from app.application.services.ai_service import AIService
ai = AIService()
response = ai.get_response([{'role': 'user', 'content': 'Hello'}])
assert response, 'AI service failed'
print('✓ AI integration test passed')
"
```

---

## 📞 Support & Troubleshooting

### Common Issues

**1. Database connection failed**
```
Error: could not translate host name "localhost" to address
Solution: Check DATABASE_URL in .env, ensure PostgreSQL is running
```

**2. Missing OpenAI key**
```
Error: OPENAI_API_KEY not found
Solution: Add OPENAI_API_KEY to .env, restart server
```

**3. Webhook authentication failed**
```
Error: Twilio signature verification failed
Solution: Verify TWILIO_AUTH_TOKEN matches Twilio console, check webhook URL
```

**4. Migration conflicts**
```
Error: Target database is not up to date
Solution: Run alembic upgrade head, or alembic stamp current
```

---

## 📈 Performance Optimization

### Database
```sql
-- Add indexes for frequent queries
CREATE INDEX idx_reservations_phone ON reservations(phone_number);
CREATE INDEX idx_hotels_active ON hotels(is_active) WHERE is_active = true;
```

### Caching
```python
# Cache hotel context (24h TTL)
@cache(ttl=86400)
def get_hotel_context():
    return hotel_service.get_context()
```

### Connection Pooling
```python
# SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
)
```

---

## ✅ Post-Deployment

1. **Verify in Production**
   ```bash
   curl https://your-domain.com/health
   # Expected: {"status": "ok"}
   ```

2. **Test WhatsApp Integration**
   - Send message via production WhatsApp number
   - Verify response received
   - Check logs for context injection

3. **Monitor First 24h**
   - Watch error rates
   - Check response times
   - Monitor database connections

4. **Setup Alerts (Optional)**
   - Notify on API errors
   - Alert on high latency
   - Monitor database health

---

## 🎯 Next Steps After Deployment

- [ ] Setup automated backups
- [ ] Configure monitoring/alerting
- [ ] Create admin dashboard
- [ ] Document runbook for operations team
- [ ] Setup CI/CD pipeline (GitHub Actions, etc)
- [ ] Plan for multi-hotel scaling
- [ ] Implement payment integration

---

**Sistema pronto para produção! 🚀**
