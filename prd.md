# 📄 PRD — Plataforma de Conversão para Creator Fitness

## 🧭 Visão do Produto

Criar uma **plataforma própria (one page + sistema de links inteligentes)** para uma creator fitness, com objetivo de:

- Centralizar recomendações e cupons  
- Aumentar conversão de parcerias  
- Medir performance de conteúdo  
- Construir um ativo independente do Instagram  

---

## 🎯 Objetivos

### Objetivos principais
- Aumentar cliques em links de afiliados/cupom
- Medir performance de cada link
- Criar um hub confiável para seguidores

### Métricas de sucesso (KPIs)
- CTR (cliques por visualização de conteúdo)
- Número de cliques por link
- Links mais acessados
- Conversão por campanha (futuro)

---

## 👤 Usuários

### Usuário principal (interno)
- Creator fitness (gestão de links e conteúdo)

### Usuário final (externo)
- Seguidores que:
  - querem comprar produtos recomendados
  - buscam cupons
  - confiam nas indicações

---

## 🧩 Escopo do Produto

### MVP (Versão 1) — Concluído ✅

#### 🔹 Frontend (One Page)
- Seção Hero (foto + nome + posicionamento)
- Lista de produtos recomendados
- Seção de cupons
- Botões de CTA (call-to-action)
- Layout mobile-first

#### 🔹 Backend (Tracking + Redirecionamento)
- Rotas dinâmicas: `/whey`, `/creatina`, `/desconto`
- Registro de cliques com timestamp e user-agent
- Redirecionamento para links externos com cupom
- Parâmetro `?src=` para identificar origem do clique

#### 🔹 Tracking básico
- Contagem de cliques por link
- Registro de data/hora
- Captura de User-Agent

---

## ⚙️ Requisitos Funcionais

### RF01 — Página principal
- Deve exibir lista de produtos com links clicáveis
- Deve carregar rapidamente (<2s)

### RF02 — Redirecionamento
- Cada rota deve:
  1. Registrar clique (link, timestamp, source, user-agent)
  2. Redirecionar usuário para destino externo

### RF03 — Tracking
- Registrar:
  - nome do link (slug)
  - timestamp UTC
  - origem (`?src=reels`, `?src=stories`, etc.)
  - user-agent do visitante

### RF04 — Painel Admin
- Rota `/admin` protegida por senha via variável de ambiente
- CRUD completo de links sem necessidade de novo deploy
- Visualização de cliques por link no próprio painel

### RF05 — Segurança de Endpoints
- Rate limiting na rota de redirecionamento `/{slug}` para evitar inflação artificial de cliques
- Endpoints de admin restritos por autenticação

---

## ⚙️ Requisitos Não Funcionais

- **Performance:** carregamento rápido (mobile prioritário, <2s)
- **Disponibilidade:** 99% uptime
- **Escalabilidade:** suporte a aumento de tráfego sem mudança de código
- **Segurança:** rate limiting em `/{slug}`, admin protegido por variável de ambiente
- **Portabilidade:** desenvolvimento local com SQLite, produção com PostgreSQL (Supabase)
- **Persistência:** dados não podem ser perdidos entre redeploys

---

## 🏗️ Arquitetura

### Frontend
- HTML5 + Vanilla JS + CSS3 (mobile-first)
- Deploy: Vercel / Netlify (arquivos estáticos servidos pelo FastAPI)

### Backend
- FastAPI + Uvicorn
- Rotas de redirecionamento com tracking
- Autenticação HTTP Basic para `/admin` via variável de ambiente

### Banco de dados

#### Estratégia dual (local vs. produção)
| Ambiente | Banco | Como configurar |
|---|---|---|
| Desenvolvimento local | SQLite (`links.db`) | `DATABASE_URL` não definida ou `sqlite:///links.db` |
| Produção | PostgreSQL via Supabase | `DATABASE_URL=postgresql://...` no `.env` |

O backend detecta automaticamente qual banco usar pela variável `DATABASE_URL`. SQLAlchemy abstrai a diferença — o código de modelos e queries permanece o mesmo.

#### Por que Supabase
- PostgreSQL gerenciado (sem self-host)
- Banco persiste entre redeploys (não depende de volume local)
- Free tier suficiente para o MVP
- Painel web para visualizar dados sem precisar de acesso ao servidor
- Suporte a conexão via connection string padrão PostgreSQL

---

## 🗂️ Modelo de Dados

### Tabela: `links`
- `id` — PK
- `slug` — único (ex: "whey")
- `title` — nome exibido
- `description` — texto de apoio (nullable)
- `destination_url` — URL externa de destino
- `coupon_code` — cupom associado (nullable)
- `category` — "produto" ou "cupom"
- `is_active` — controle de visibilidade
- `created_at` — timestamp de criação

### Tabela: `clicks`
- `id` — PK
- `link_id` — FK → links.id
- `timestamp` — data/hora do clique (UTC)
- `source` — origem do clique (nullable, ex: "reels", "stories")
- `user_agent` — navegador/dispositivo do visitante (nullable)

### Observação: seed de dados
- Links iniciais devem ser inseridos com verificação de existência (`INSERT IF NOT EXISTS`)
- Evitar duplicação ao reiniciar o servidor

---

## 🚀 Roadmap de Evolução

---

### 🟢 Fase 1 — MVP (Concluído ✅)
- One page com lista de produtos e cupons
- Links com redirecionamento e tracking básico
- Parâmetro `?src=` implementado
- User-agent capturado
- Redesign visual: Playfair Display + Nunito, rosa #F25C8A, hero com foto, seção sobre mim, strip decorativo, cards animados, cupom com botão copiar

---

### 🟢 Fase 2 — Deploy & Infraestrutura (Concluído ✅)

#### Objetivo:
Tornar o projeto acessível publicamente com dados persistentes entre redeploys.

#### Tasks:
- ✅ Configurar variável `DATABASE_URL` para alternar entre SQLite (local) e PostgreSQL (produção)
- ✅ Criar projeto no Supabase e obter connection string (Session Pooler, sa-east-1)
- ✅ Adicionar `psycopg2-binary` e `python-dotenv` ao `requirements.txt`
- ✅ Criar arquivo `.env.example` com as variáveis necessárias
- ✅ Corrigir seed de dados para usar upsert por slug
- ✅ Criar `Procfile` para deploy no Render
- ✅ MCP do Supabase configurado no projeto
- ✅ Fazer deploy no Render e configurar variáveis de ambiente

#### Valor:
- Projeto online e acessível
- Dados persistentes — cliques e links não se perdem

---

### 🟡 Fase 3 — Painel Admin

#### Features:
- Rota protegida por senha (`/admin`)
- Autenticação simples via variável de ambiente `ADMIN_PASSWORD` (sem cadastro)
- CRUD de links: adicionar, editar, remover sem novo deploy
- Visualização de cliques por link diretamente no painel

#### Segurança:
- HTTP Basic Auth ou token estático via header
- Senha definida em variável de ambiente — nunca hardcoded

#### Valor:
- Autonomia total para gerenciar links sem depender de código
- Base para gestão de cupons e campanhas nas fases seguintes

---

### 🟡 Fase 4 — Analytics

#### Features:
- Dashboard simples (no próprio painel admin ou página separada):
  - cliques por link
  - cliques por dia
  - cliques por origem (`src`)
- Filtros básicos por período

#### Valor:
- Entender o que gera resultado
- Base para decisões de conteúdo e negociação com marcas

---

### 🟡 Fase 5 — Tracking Avançado

#### Features:
- Identificação automática de origem por referrer HTTP
- Parâmetros dinâmicos padronizados (`?src=reels`, `?src=stories`, `?src=bio`)
- Rate limiting na rota `/{slug}` para evitar cliques artificiais

#### Valor:
- Saber qual conteúdo converte mais sem depender de parâmetro manual

---

### 🔴 Fase 6 — Otimização de Conversão

#### Features:
- A/B testing de links (diferentes destinos por campanha)
- CTAs dinâmicos por origem
- Agendamento de links ativos por período

---

### 🔴 Fase 7 — Plataforma Completa

#### Features:
- Gestão de cupons com data de validade
- Página de rotina (ex: `/rotina-manha`)
- Páginas específicas por campanha

---

### 🔴 Fase 8 — Monetização & Escala

#### Features:
- Integração com redes de afiliados
- Tracking de conversão (se possível via pixel/postback)
- Relatórios exportáveis para marcas
- Multi-creator (expandir para outros perfis)

---

## 🎨 Design & Identidade Visual

### Estilo geral
- **Tom:** lifestyle pessoal — caloroso, próximo, autêntico. Não é uma loja, é a página de uma pessoa real
- **Estética:** alegre, vibrante, com energia positiva. Evitar aparência clínica ou genérica de "link-in-bio"
- **Público:** majoritariamente feminino, acessa pelo celular

### Paleta de cores
| Papel | Direção |
|---|---|
| Cor primária | Rosa — tom vibrante mas não agressivo (ex: `#F25C8A` ou similar) |
| Cor de apoio | Branco ou off-white para respiro e leitura |
| Acento | Um tom quente complementar (pêssego, coral ou lilás claro) |
| Texto | Quase-preto (não preto puro) para suavizar |

> A paleta exata deve ser definida junto com a Clara antes da implementação do novo frontend.

### Tipografia
- **Títulos:** fonte com personalidade — script ou sans-serif arredondada (ex: Poppins, Nunito, ou uma display font para o nome)
- **Corpo:** sans-serif limpa e legível no mobile
- Evitar fontes genéricas como Arial ou Roboto puro

### Fotografia
| Seção | Uso |
|---|---|
| Hero | Foto principal da Clara — expressão alegre, boa iluminação, fundo neutro ou vibrante |
| Seção "Sobre mim" | Foto mais casual/lifestyle — pode ser em movimento, treino, ou dia a dia |

- Fotos devem ter alta resolução e ser otimizadas para web (formato WebP)
- A foto da hero é o elemento visual mais importante da página — deve transmitir confiança e simpatia

### Seções da página (ordem sugerida)
1. **Hero** — foto dela + nome + frase de posicionamento curta + CTA principal
2. **Sobre mim** — parágrafo curto e pessoal, foto secundária, tom de conversa
3. **Produtos recomendados** — cards com foto do produto, nome, descrição curta e botão
4. **Cupons** — destaque visual (badge ou card diferenciado), código copiável
5. **Rodapé** — redes sociais, @instagram

### Componentes visuais
- Botões com bordas arredondadas (pill shape), cor primária
- Cards de produto com sombra suave, sem bordas rígidas
- Espaçamento generoso — página deve "respirar"
- Sem poluição visual: uma coisa de cada vez na tela do celular

### O que evitar
- Fundo preto ou escuro (quebra o tom alegre)
- Muitas cores competindo ao mesmo tempo
- Ícones ou elementos de estoque genéricos
- Aparência de "template de Linktree"

---

## 🔥 Diferenciais do Produto

- Controle total dos links
- Dados próprios (não depender de plataformas de terceiros)
- Capacidade de otimizar conversão com dados reais
- Base para negociações com marcas

---

## ⚠️ Riscos

### Técnicos
- **Perda de dados entre redeploys** — resolvido com Supabase (PostgreSQL persistente)
- **Inflação de cliques** — mitigado com rate limiting na Fase 5
- **Endpoints públicos sem proteção** — `/api/stats` e `/api/links` são somente leitura, risco baixo; admin será protegido na Fase 3
- **Seed duplicado** — corrigir para `INSERT IF NOT EXISTS` antes do deploy

### De negócio
- Baixo tráfego inicial
- Dependência de consistência de conteúdo
- Falta de uso dos dados coletados

---

## 📌 Futuras Ideias

- Encurtador estilo Bitly próprio
- Integração com automação (DM)
- Heatmap de cliques
- Sistema de recomendação baseado em performance

---

## ✅ Definição de Pronto (MVP)

- [x] Página publicada e acessível
- [x] Pelo menos 3 links funcionando
- [x] Tracking registrando cliques
- [x] Redirecionamento funcionando corretamente

## ✅ Definição de Pronto (Deploy)

- [ ] Aplicação acessível via URL pública
- [ ] Banco PostgreSQL no Supabase conectado
- [ ] Dados persistem entre redeploys
- [ ] Variáveis de ambiente configuradas no servidor
- [ ] `.env.example` documentado no repositório
