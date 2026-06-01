# Instalacao local no Windows - Conciliador NF x Etiquetas

Este guia explica como instalar, iniciar automaticamente, verificar e parar o sistema **Conciliador NF x Etiquetas** em um computador Windows usado como maquina principal da empresa.

O sistema roda localmente, sem hospedagem online:

- Backend FastAPI: `http://localhost:8010`
- Frontend React/Vite: `http://localhost:8080`

## Uso com GitHub e computador principal

Se este computador for apenas de desenvolvimento, suba para o GitHub somente o projeto, os scripts e a documentacao. Nao suba pastas geradas ou dependencias locais como:

- `backend\.venv`
- `frontend\node_modules`
- `frontend\dist`
- `.runtime`

Essas pastas ja ficam ignoradas pelo `.gitignore` ou devem ser recriadas no computador principal.

Fluxo recomendado:

1. No computador de desenvolvimento, envie o projeto para o GitHub.
2. No computador principal da empresa, clone ou baixe o projeto.
3. No computador principal, instale Python, Node.js e as dependencias conforme este guia.
4. No computador principal, teste:

```text
iniciar_conciliador.bat
verificar_conciliador.bat
```

5. Somente no computador principal, instale a tarefa agendada:

```text
instalar_tarefa_agendada_conciliador.bat
```

Importante: a tarefa agendada guarda o caminho local do arquivo `iniciar_conciliador_oculto.ps1`. Por isso, ela precisa ser criada no computador principal depois que o projeto ja estiver na pasta final.

## Arquivos criados

Na raiz do projeto existem estes arquivos de operacao:

- `iniciar_conciliador.bat`: valida as pastas e inicia backend e frontend em janelas minimizadas.
- `iniciar_backend_conciliador.bat`: script interno usado para iniciar o FastAPI.
- `iniciar_frontend_conciliador.bat`: script interno usado para servir o frontend na porta `8080`.
- `iniciar_conciliador_oculto.ps1`: alternativa para iniciar com janelas ocultas, indicada para o Agendador de Tarefas.
- `instalar_tarefa_agendada_conciliador.bat`: cria a tarefa no Agendador de Tarefas do Windows.
- `remover_tarefa_agendada_conciliador.bat`: remove a tarefa criada no Agendador de Tarefas.
- `verificar_conciliador.bat`: testa se backend e frontend estao respondendo.
- `parar_conciliador.bat`: encerra os processos iniciados pelo sistema e libera as portas `8010` e `8080`.

## Instalacao pela primeira vez

Execute estes passos uma vez no computador principal.

### 1. Instalar Python

Instale o Python para Windows, de preferencia uma versao recente.

Durante a instalacao, marque a opcao:

```text
Add python.exe to PATH
```

Depois confirme no Prompt de Comando:

```bat
python --version
```

### 2. Instalar Node.js

Instale o Node.js LTS para Windows.

Depois confirme no Prompt de Comando:

```bat
node --version
npm --version
```

### 3. Instalar dependencias do backend

Na raiz do projeto, execute:

```bat
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..
```

O script de inicializacao espera encontrar:

```text
backend\.venv\Scripts\activate.bat
```

### 4. Instalar dependencias do frontend

Na raiz do projeto, execute:

```bat
cd frontend
npm install
cd ..
```

O script de inicializacao espera encontrar:

```text
frontend\node_modules
```

## Como testar manualmente

Na raiz do projeto, de duplo clique em:

```text
iniciar_conciliador.bat
```

Ele deve validar:

- se a pasta `backend` existe;
- se a pasta `frontend` existe;
- se o ambiente virtual `backend\.venv` existe;
- se `frontend\node_modules` existe.

Se algo estiver faltando, o script mostra uma mensagem de erro com a solucao.

Depois de iniciar, aguarde alguns segundos e acesse:

```text
http://localhost:8080
```

Observacao: para uso operacional, o frontend e servido a partir do build em `frontend\dist` usando `npm run preview -- --host 0.0.0.0 --port 8080`. Se `dist` nao existir, o script gera o build automaticamente antes de iniciar.

Para verificar pelo script:

```text
verificar_conciliador.bat
```

## Como iniciar junto com o Windows usando shell:startup

Esta e a opcao mais simples. Ela inicia o sistema quando o usuario do Windows fizer login.

1. Pressione `Windows + R`.
2. Digite:

```text
shell:startup
```

3. Clique em OK.
4. Na pasta que abrir, crie um atalho para:

```text
iniciar_conciliador.bat
```

5. Reinicie o computador ou saia e entre novamente no usuario do Windows.

Observacao: esta opcao pode deixar janelas minimizadas abertas. Para uso simples em uma empresa, costuma ser suficiente e facil de manter.

## Como iniciar junto com o Windows usando Agendador de Tarefas

Esta e a opcao mais limpa para operacao diaria. O sistema pode iniciar no login do usuario com janela oculta.

### Opcao automatica

Na raiz do projeto, execute:

```text
instalar_tarefa_agendada_conciliador.bat
```

Se o Windows pedir permissao, confirme. O script cria a tarefa:

```text
Conciliador NF x Etiquetas
```

Ela sera executada automaticamente quando o usuario fizer login no Windows.

Para testar a tarefa sem reiniciar, abra o Prompt de Comando como Administrador e execute:

```bat
schtasks /Run /TN "Conciliador NF x Etiquetas"
```

Depois acesse:

```text
http://localhost:8080
```

Para remover essa inicializacao automatica:

```text
remover_tarefa_agendada_conciliador.bat
```

### Opcao manual

1. Abra o Menu Iniciar.
2. Pesquise por `Agendador de Tarefas`.
3. Clique em `Criar Tarefa...`.
4. Na aba `Geral`:
   - Nome: `Conciliador NF x Etiquetas`
   - Marque `Executar somente quando o usuario estiver conectado`.
   - Opcional: marque `Executar com privilegios mais altos`.
5. Na aba `Disparadores`:
   - Clique em `Novo...`.
   - Escolha `Ao fazer logon`.
   - Confirme.
6. Na aba `Acoes`:
   - Clique em `Novo...`.
   - Programa/script:

```text
powershell.exe
```

   - Adicione argumentos:

```text
-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\CAMINHO\DO\PROJETO\iniciar_conciliador_oculto.ps1"
```

Troque `C:\CAMINHO\DO\PROJETO` pela pasta real onde o projeto esta instalado.

7. Na aba `Condicoes`, desmarque opcoes que impecam a execucao fora da tomada, se for um notebook.
8. Salve a tarefa.
9. Clique com o botao direito na tarefa e use `Executar` para testar.

## Como saber se o backend esta rodando

Abra no navegador do computador principal:

```text
http://localhost:8010/api/health
```

Resultado esperado:

```json
{"status":"ok"}
```

Tambem e possivel executar:

```text
verificar_conciliador.bat
```

## Como saber se o frontend esta rodando

Abra no navegador:

```text
http://localhost:8080
```

Se a tela do Conciliador abrir, o frontend esta funcionando.

Tambem e possivel executar:

```text
verificar_conciliador.bat
```

## Como acessar no computador principal

No computador onde o sistema esta rodando:

```text
http://localhost:8080
```

ou:

```text
http://127.0.0.1:8080
```

## Como acessar de outro computador da rede

Use o IP do computador principal.

Exemplo:

```text
http://192.168.0.50:8080
```

O backend ficara em:

```text
http://192.168.0.50:8010/api/health
```

Os dois computadores precisam estar na mesma rede local.

## Como descobrir o IP do computador principal

No computador principal:

1. Pressione `Windows + R`.
2. Digite:

```text
cmd
```

3. Execute:

```bat
ipconfig
```

4. Procure por `Endereco IPv4` ou `IPv4 Address`.

Exemplo:

```text
Endereco IPv4 . . . . . . . . . . . . : 192.168.0.50
```

Neste exemplo, outros computadores acessariam:

```text
http://192.168.0.50:8080
```

## Como liberar as portas no Firewall do Windows

Para permitir acesso de outros computadores da rede, libere as portas `8010` e `8080`.

Abra o Prompt de Comando ou PowerShell como Administrador e execute:

```bat
netsh advfirewall firewall add rule name="Conciliador Backend 8010" dir=in action=allow protocol=TCP localport=8010
netsh advfirewall firewall add rule name="Conciliador Frontend 8080" dir=in action=allow protocol=TCP localport=8080
```

Se preferir pela interface:

1. Abra `Firewall do Windows Defender com Seguranca Avancada`.
2. Entre em `Regras de Entrada`.
3. Clique em `Nova Regra...`.
4. Escolha `Porta`.
5. Escolha `TCP`.
6. Informe `8010,8080`.
7. Marque `Permitir a conexao`.
8. Aplique aos perfis adequados da rede local.
9. Nomeie como `Conciliador NF x Etiquetas`.

## Como parar o sistema

Na raiz do projeto, de duplo clique em:

```text
parar_conciliador.bat
```

O script tenta encerrar:

- o backend salvo em `.runtime\backend.pid`;
- o frontend salvo em `.runtime\frontend.pid`;
- qualquer processo escutando nas portas `8010` e `8080`.

Importante: se outro programa estiver usando essas portas, ele tambem pode ser encerrado. Use portas dedicadas para o Conciliador.

## Problemas comuns e solucoes

### Erro: A pasta backend nao foi encontrada

O arquivo `iniciar_conciliador.bat` precisa estar na raiz do projeto, ao lado das pastas `backend` e `frontend`.

### Erro: A pasta frontend nao foi encontrada

Verifique se a estrutura do projeto esta completa:

```text
backend
frontend
iniciar_conciliador.bat
```

### Erro: O ambiente virtual do backend nao foi encontrado

Instale o ambiente virtual:

```bat
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..
```

### Erro: frontend\node_modules nao foi encontrado

Instale as dependencias do frontend:

```bat
cd frontend
npm install
cd ..
```

### O frontend nao inicia com npm run dev

Em algumas maquinas Windows, o servidor de desenvolvimento do Vite pode falhar ao otimizar dependencias. Para operacao local, os scripts usam o modo mais estavel:

```bat
npm run build
npm run preview -- --host 0.0.0.0 --port 8080
```

Esse e o modo recomendado para o computador da empresa.

### O navegador nao abre http://localhost:8080

Execute:

```text
verificar_conciliador.bat
```

Se backend ou frontend nao responderem, pare e inicie novamente:

```text
parar_conciliador.bat
iniciar_conciliador.bat
```

### Outro computador nao consegue acessar

Confira:

- se esta usando o IP correto do computador principal;
- se ambos estao na mesma rede;
- se o firewall liberou as portas `8010` e `8080`;
- se o sistema foi iniciado com `--host 0.0.0.0`, como nos scripts criados.

### Porta ja esta em uso

Algum processo ja esta usando `8010` ou `8080`.

Execute:

```text
parar_conciliador.bat
```

Depois tente iniciar novamente.

### O Agendador de Tarefas nao inicia

Confira:

- se o caminho do arquivo `iniciar_conciliador_oculto.ps1` esta correto;
- se o usuario do Windows tem permissao para acessar a pasta do projeto;
- se Python, Node.js e dependencias foram instalados para esse usuario;
- se a tarefa esta configurada para executar ao fazer logon.

## Cuidados antes de usar na empresa

- Teste o sistema por alguns dias iniciando manualmente antes de ativar a inicializacao automatica.
- Use um computador principal estavel, que nao seja desligado durante o expediente.
- Configure um IP fixo ou reserva de DHCP para o computador principal, se outros computadores forem acessar pela rede.
- Evite usar as portas `8010` e `8080` para outros sistemas no mesmo computador.
- Mantenha uma copia do projeto e dos arquivos de configuracao.
- Depois de alterar dependencias, teste novamente `iniciar_conciliador.bat`, `verificar_conciliador.bat` e `parar_conciliador.bat`.
