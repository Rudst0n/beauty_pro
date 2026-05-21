# Beauty Pro

Sistema web em Flask para salão de beleza, cabeleireira, estética, barbearia e pequenos negócios que desejam divulgar serviços, vender produtos e receber contatos pelo WhatsApp.

O projeto funciona como uma landing page profissional com catálogo, painel administrativo, relatórios de cliques e estrutura preparada para multiempresas.

## Objetivo do sistema

O Beauty Pro foi criado para transformar a presença digital de pequenos negócios em uma vitrine profissional.

A cliente final acessa o site, visualiza produtos, serviços, fotos e informações do salão. Ao clicar em comprar ou agendar, ela é direcionada diretamente para o WhatsApp com uma mensagem pronta.

A dona do salão acessa um painel administrativo para gerenciar produtos, serviços, fotos, configurações e relatórios.

A CodeCraft acessa o Painel Master para administrar empresas/clientes dentro do mesmo sistema.

## O que já vem pronto

1. Landing page pública
2. Catálogo de produtos
3. Lista de serviços
4. Galeria de fotos
5. Botões com redirecionamento para WhatsApp
6. Registro automático de cliques
7. Painel administrativo com login
8. Cadastro, edição e exclusão de produtos
9. Cadastro, edição e exclusão de serviços
10. Cadastro, edição e exclusão de fotos da galeria
11. Configurações do salão
12. Dashboard com indicadores
13. Relatórios de produtos mais procurados
14. Relatórios de serviços mais acessados
15. Histórico de cliques
16. Proteção CSRF nos formulários
17. Upload limitado a imagens
18. Rotas administrativas protegidas por login
19. Painel Master da CodeCraft
20. Estrutura pronta para multiempresas

## Perfis de acesso

### Painel Master da CodeCraft

Acesso destinado à CodeCraft para administrar empresas/clientes cadastrados no sistema.

Permite:

1. Visualizar empresas cadastradas
2. Criar novas empresas
3. Editar dados das empresas
4. Ativar empresas
5. Inativar empresas
6. Bloquear empresas
7. Acompanhar indicadores gerais
8. Administrar vários clientes no mesmo sistema

### Painel da empresa

Acesso destinado ao cliente, por exemplo a dona do salão.

Permite:

1. Cadastrar produtos
2. Editar preços
3. Cadastrar serviços
4. Postar fotos na galeria
5. Alterar dados do salão
6. Visualizar relatórios de cliques
7. Acompanhar produtos e serviços mais procurados

## Como rodar no Windows

Abra o terminal na pasta do projeto e rode:

```powershell
python -m venv .venv
```

Caso o PowerShell bloqueie a ativação do ambiente virtual, rode:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Ative o ambiente virtual:

```powershell
.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

Crie o arquivo de ambiente:

```powershell
copy .env.example .env
```

Crie o banco inicial:

```powershell
flask --app run.py init-db
```

Rode o sistema:

```powershell
flask --app run.py run
```

Depois acesse:

```text
Site público: http://127.0.0.1:5000/salao-modelo
Painel: http://127.0.0.1:5000/admin/login
Painel Master: http://127.0.0.1:5000/admin/master
```

## Como rodar no Linux

Crie o ambiente virtual:

```bash
python3 -m venv .venv
```

Ative o ambiente:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o arquivo de ambiente:

```bash
cp .env.example .env
```

Crie o banco inicial:

```bash
flask --app run.py init-db
```

Rode o sistema:

```bash
flask --app run.py run
```

Depois acesse:

```text
Site público: http://127.0.0.1:5000/salao-modelo
Painel: http://127.0.0.1:5000/admin/login
Painel Master: http://127.0.0.1:5000/admin/master
```

## Login inicial

O sistema possui um usuário administrativo inicial para ambiente local.

```text
E-mail: admin@codecraft.com
```

A senha inicial deve ser alterada antes de qualquer demonstração ou uso real.

No ambiente atual de desenvolvimento, utilize a senha definida manualmente no banco de dados.

## Como alterar a senha do usuário inicial

Entre no shell do Flask:

```powershell
.venv\Scripts\python.exe -m flask --app run.py shell
```

Depois execute:

```python
from app.extensions import db
from app.models import User

user = User.query.filter_by(email="admin@codecraft.com").first()
user.set_password("NovaSenhaForteAqui")
db.session.commit()

print("Senha alterada com sucesso.")
```

Para sair:

```python
exit()
```

## Como o relatório funciona

Quando uma pessoa clica em um produto, serviço, WhatsApp, Instagram ou localização, o sistema salva um registro na tabela `click_events`.

Exemplo:

```text
Tipo: product
Item: Kit Hidratação
Ação: whatsapp_click
Origem: Instagram ou direct
Data: data e hora do clique
```

Com esses dados, o painel mostra:

1. Total de cliques
2. Produtos mais procurados
3. Serviços mais acessados
4. Cliques no WhatsApp
5. Histórico recente
6. Gráfico de cliques por dia

## Rotas principais

```text
/                         redireciona para a primeira empresa ativa
/salao-modelo             site público da empresa
/admin/login              login do painel
/admin/dashboard          painel inicial da empresa
/admin/produtos           gestão de produtos
/admin/servicos           gestão de serviços
/admin/galeria            gestão de fotos
/admin/relatorios         relatórios de cliques
/admin/configuracoes      dados do salão
/admin/master             painel master da CodeCraft
```

## Estrutura geral

```text
beauty_pro/
  app/
    blueprints/
      admin/
      public/
    static/
      css/
      js/
      uploads/
    templates/
      admin/
      public/
    models.py
    extensions.py
    config.py
    utils.py
  instance/
  requirements.txt
  run.py
  README.md
  .env.example
  .gitignore
```

## Melhorias já aplicadas

- Controle de estoque por produto
- Tela administrativa de estoque
- Histórico de movimentações de estoque
- Bloqueio de compra pública para produto esgotado

1. CSRF nos formulários administrativos
2. Proteção no login e logout
3. Proteção nas ações de cadastro, edição e exclusão
4. Upload limitado a imagens
5. Rotas administrativas protegidas por login
6. Registro automático de cliques
7. Relatórios de produtos e serviços mais acessados
8. Estrutura multiempresa com `company_id`
9. Painel Master da CodeCraft
10. Separação entre usuário master e usuário comum da empresa
11. Configurações individuais por empresa
12. Redirecionamento inteligente conforme o tipo de usuário

## Próximos upgrades recomendados

1. Recuperação de senha
3. Agendamento com calendário
4. Cadastro de clientes
5. Cupons e campanhas
6. Pagamento online por Pix ou checkout
7. Planos e cobrança mensal por empresa
8. Deploy com PostgreSQL
9. Backup automático do banco e dos uploads
10. Melhorias visuais para apresentação comercial
11. Página de vendas própria do produto
12. Personalização avançada por empresa
13. Logs administrativos
14. Níveis de permissão mais detalhados
15. Opção para a CodeCraft entrar como cliente

## Observação importante

Este projeto já está estruturado para evoluir como produto da CodeCraft.

Mesmo começando com uma cliente, o banco já usa `company_id`, permitindo vender o mesmo sistema para outros negócios no futuro.

A estrutura atual permite atender diferentes empresas dentro do mesmo sistema, mantendo produtos, serviços, fotos, configurações e relatórios separados por empresa.

## Segurança

Antes de colocar em produção:

1. Alterar a senha padrão
2. Definir uma `SECRET_KEY` segura no arquivo `.env`
3. Não subir `.env` para o GitHub
4. Não subir `.venv`
5. Não subir o banco local da pasta `instance`
6. Não subir uploads de teste
7. Configurar banco PostgreSQL
8. Configurar backup
9. Configurar domínio e HTTPS
10. Revisar permissões de usuários

## Arquivos que não devem ser enviados para o GitHub

O `.gitignore` deve impedir o envio de:

```text
.venv/
.env
instance/
app/static/uploads/
__pycache__/
*.pyc
.pytest_cache/
htmlcov/
.vscode/
```

## Deploy recomendado

Para produção, recomenda-se usar:

1. Servidor Linux
2. Ambiente virtual Python
3. Banco PostgreSQL
4. Variáveis de ambiente no `.env`
5. HTTPS ativo
6. Domínio configurado
7. Backup do banco
8. Backup da pasta de uploads
9. Serviço de aplicação com Gunicorn
10. Proxy reverso com Nginx

## Resumo comercial

O Beauty Pro é uma solução da CodeCraft para pequenos negócios que precisam de uma presença digital mais profissional.

Ele permite divulgar serviços, vender produtos pelo WhatsApp, postar fotos, acompanhar relatórios e administrar tudo por um painel simples.

A CodeCraft consegue usar esse mesmo sistema para atender vários clientes, mantendo cada empresa com suas próprias informações, produtos, serviços, fotos e relatórios.