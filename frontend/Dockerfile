# Dockerfile para frontend React/Vite
FROM node:20-alpine

# Diretório de trabalho
WORKDIR /app

# Build arg para URL da API (default: localhost para dev local)
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copia package.json e package-lock.json (se existir)
COPY package*.json ./

# Instala dependências
RUN npm install

# Copia o restante do código
COPY . .

# Build da aplicação
RUN npm run build

# Exponha a porta padrão do Vite preview
EXPOSE 4173

# Comando padrão: servir build em preview
CMD ["npm", "run", "preview"]
