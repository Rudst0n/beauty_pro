# BeautyCatalog Pro

Sistema em Flask para salão de beleza, cabeleireira, estética, barbearia e pequenos negócios que desejam vender produtos e receber agendamentos pelo WhatsApp.

## O que já vem pronto

- Landing page pública
- Catálogo de produtos
- Lista de serviços
- Galeria de fotos
- Botões com redirecionamento para WhatsApp
- Registro automático de cliques
- Painel administrativo com login
- Cadastro, edição e exclusão de produtos
- Cadastro, edição e exclusão de serviços
- Cadastro, edição e exclusão de fotos da galeria
- Configurações do salão
- Dashboard com indicadores
- Relatórios de produtos mais procurados
- Relatórios de serviços mais acessados
- Histórico de cliques
- Estrutura pronta para multiempresas

## Como rodar no Windows

Abra o terminal na pasta do projeto e rode:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app run.py init-db
flask --app run.py run
```

Depois acesse:

```text
Site público: http://127.0.0.1:5000/salao-modelo
Painel: http://127.0.0.1:5000/admin/login
```

Login inicial:

```text
E-mail: admin@codecraft.com
Senha: 123456
```

## Como rodar no Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app run.py init-db
flask --app run.py run
```

Depois acesse:

```text
Site público: http://127.0.0.1:5000/salao-modelo
Painel: http://127.0.0.1:5000/admin/login
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

- Total de cliques
- Produtos mais procurados
- Serviços mais acessados
- Cliques no WhatsApp
- Histórico recente
- Gráfico de cliques por dia

## Rotas principais

```text
/                         redireciona para a primeira empresa ativa
/salao-modelo             site público da empresa
/admin/login              login do painel
/admin/dashboard          painel inicial
/admin/produtos           gestão de produtos
/admin/servicos           gestão de serviços
/admin/galeria            gestão de fotos
/admin/relatorios         relatórios de cliques
/admin/configuracoes      dados do salão
```

## Próximos upgrades recomendados

1. CSRF nos formulários FEITO
2. Recuperação de senha
3. Controle de estoque
4. Agendamento com calendário
5. Cadastro de clientes
6. Cupons e campanhas
7. Pagamento online por Pix ou checkout
8. Planos e cobrança mensal por empresa
9. Deploy com PostgreSQL
10. Painel master da CodeCraft para administrar vários clientes


## Melhorias já aplicadas

1. CSRF nos formulários administrativos
2. Proteção no login e logout
3. Proteção nas ações de cadastro, edição e exclusão
4. Upload limitado a imagens
5. Rotas administrativas protegidas por login

## Observação importante

Este projeto já está estruturado para evoluir como produto da CodeCraft. Mesmo começando com uma cliente, o banco já usa `company_id`, permitindo vender o mesmo sistema para outros negócios no futuro.
