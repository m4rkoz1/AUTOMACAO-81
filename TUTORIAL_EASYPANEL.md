# Tutorial de Instalação no Easypanel

Este tutorial explica como realizar o deploy da **Automação SSW** no Easypanel. O projeto exige o Playwright, o que requer uma imagem Docker específica configurada (que já foi providenciada neste repositório).

## 1. Criar o Projeto e o App no Easypanel

1. Acesse o painel do seu Easypanel.
2. Na aba **Projects**, crie um novo projeto (ex: `automacao-ssw`).
3. Clique no projeto criado e clique em **Create App**.
4. Dê um nome para a aplicação (ex: `ssw-bot`).

## 2. Configurar a Fonte (Source)

Na página do seu App recém-criado, vá na aba **Source** e configure:

1. **Source Type**: Selecione **Github** (ou Git).
2. **Repository**: Informe o link do repositório: `m4rkoz1/AUTOMACAO-81` (ou a URL completa dependendo de como o Easypanel pede).
3. **Branch**: `main` (ou a branch onde este código está).
4. **Build Method**: Selecione **Dockerfile**. O Easypanel detectará automaticamente o arquivo `Dockerfile` na raiz do projeto, que já contém todas as dependências do Playwright e configurações de fuso horário.

Clique em **Save**.

## 3. Configurar Variáveis de Ambiente (Opcional)

Se você precisar de variáveis secretas (senhas), vá na aba **Environment** e as defina. 
Atualmente, o projeto usa os dados do `inputs.txt` localmente. Garanta que suas credenciais estão seguras.

## 4. Portas (Network)

1. Vá para a aba **Network**.
2. O servidor roda internamente na porta **5000**.
3. Em **Domains**, você pode adicionar um domínio próprio se desejar (ex: `automacao.seusite.com`) e o Easypanel fará o roteamento para a porta interna 5000 automaticamente, gerando também o SSL.

## 5. Deploy

1. Vá na aba **Deploy**.
2. Clique no botão azul **Deploy**.
3. Aguarde o painel construir a imagem Docker. Esse processo pode levar de 3 a 5 minutos, pois o comando `playwright install --with-deps chromium` irá baixar as dependências do Google Chrome.

## 6. Pronto!

Após o build finalizar, você poderá acessar a URL do seu App e ver a tela de Agendador da Automação SSW! Todos os downloads de planilhas ficarão disponíveis no armazenamento local do contêiner.

### Observações sobre o Linux/Docker
- A funcionalidade "Abrir RJO" no frontend que rodava o Excel foi desativada em ambientes Linux, visto que não há interface gráfica para abrir o Excel do lado do servidor. Os arquivos podem ser baixados via requisição de Download como de costume no Power BI ou no Frontend.
