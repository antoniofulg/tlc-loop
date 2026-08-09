# Plano — Roteamento explícito de batches por stage

**Objetivo:** permitir que cada batch do `tlc-loop` use um provider/modelo
diferente conforme o domínio do trabalho, sem inferir a rota pelo título da
phase e sem alterar o comportamento de features antigas.

**Resultado esperado:** `tlc-spec-driven` continua responsável por criar e
aprovar o `tasks.md`. Quando o usuário invoca os dois skills, `tlc-loop`
fornece o contrato de compatibilidade e valida o campo `**Stage:**` de cada
phase antes da aprovação e novamente no bootstrap.

**Escopo de código:** somente `tlc-loop`.

**Integração opt-in:** `tlc-spec-driven` não muda. O contrato só é aplicado
quando o usuário nomeia os dois skills. Sem `$tlc-loop`, a autoria de Tasks
continua genérica.

---

## 1. Modelo

Três conceitos permanecem separados:

- **Phase:** unidade semântica e de dependência criada durante Tasks. É
  indivisível.
- **Stage:** rota operacional de uma phase, declarada por `**Stage:**`. Escolhe
  a configuração em `[stages.<nome>]`.
- **Batch:** unidade de execução. Contém uma ou mais phases inteiras,
  consecutivas e com o mesmo stage efetivo.

Exemplo:

```markdown
### Phase 1: Preparação compartilhada

**Stage:** foundation

### Phase 2: API de checkout

**Stage:** backend

### Phase 3: Tela de checkout

**Stage:** frontend

### Phase 4: Documentação operacional

**Stage:** docs
```

O título descreve o propósito. `Stage` decide o executor. O loop nunca deriva
rota de palavras, travessões ou capitalização do título.

---

## 2. Estado atual

### `tlc-spec-driven`

A fase Tasks agrupa trabalho por dependência e coesão. O template padrão usa
`Foundation`, `Core Implementation` e `Integration`. O tamanho alvo já é
próximo de sete tasks por phase, com teto aproximado de dez.

Essa estrutura é correta para execução genérica, mas uma phase horizontal pode
misturar backend e frontend. Um único worker recebe tudo.

### `tlc-loop`

O loop já possui as peças básicas:

- `_config.py` aceita qualquer `[stages.<nome>]`.
- `resolve_stage.py` resolve qualquer stage configurado.
- `_batching.py` preserva phases inteiras e consecutivas.
- `detect_phase.py` escolhe o próximo batch.

O ponto fixo está no dispatch da Phase B:

```bash
python3 <skill-dir>/scripts/resolve_stage.py --stage implement ...
```

Todo batch ainda usa `implement`.

### Falhas que este plano elimina

- Rota inferida por título pode falhar silenciosamente.
- Comparar slugs brutos muda batches mesmo quando todos caem em `implement`.
- `strict_routing` não pode tratar fallback intencional e typo da mesma forma.
- `Phase 2a` e `Phase 2b` colidem no parser atual.
- Um título `Verify` ou `Fix` pode colidir com stages reservados.
- O stage escolhido precisa atravessar `detect_phase.py` até o dispatch.

---

## 3. Decisões

### D1 — `**Stage:**` explícito é a única fonte da rota

Formato canônico:

```markdown
### Phase 2: API de checkout

**Stage:** backend
```

Regras:

- `Stage` é a primeira linha não vazia depois do cabeçalho da phase.
- O valor usa minúsculas e kebab-case: `[a-z][a-z0-9-]*`.
- O valor deve corresponder exatamente a `[stages.<valor>]`.
- O título não participa da resolução.
- Uma phase possui zero ou um campo `Stage`; duplicidade é erro.

**Rejeitado:** derivar stage do último segmento do título. O título é conteúdo
humano e muda por legibilidade. Rota é configuração operacional e precisa de
um campo próprio.

### D2 — Integração por invocação dupla, sem mudar `tlc-spec-driven`

Forma curta recomendada:

```text
$tlc-spec-driven crie as tasks da feature <nome> para execução pelo $tlc-loop,
com phases separadas por stage.
```

Forma explícita quando o usuário quer sugerir domínios:

```text
$tlc-spec-driven crie as tasks da feature <nome> para execução pelo $tlc-loop.
Separe as phases por stage, priorizando foundation, backend, frontend e docs
conforme .specs/loop.config.toml.
```

Responsabilidades:

- `tlc-spec-driven` continua dono do processo Tasks, granularidade,
  dependências, testes e aprovação.
- `tlc-loop` contribui apenas com seu contrato de compatibilidade para
  `tasks.md` e com o validador de rotas.
- Nomear `$tlc-loop` durante Tasks não inicia o loop. O Execute continua
  proibido até o `tasks.md` ser aprovado.
- Se o usuário invocar apenas `$tlc-spec-driven`, nenhum stage é exigido.

O `SKILL.md` de `tlc-loop` passa a apontar para
`references/tasks-routing-contract.md` quando for nomeado ao lado de um skill
autor de Tasks. Isso transforma a frase curta em contrato verificável, sem
repetir todas as regras no prompt.

### D3 — Dependência e coesão continuam acima do domínio

O autor aplica estas regras ao preparar o Execution Plan:

1. Preservar a ordem de dependência.
2. Cada phase usa um único stage.
3. Tasks que exigem stages diferentes não ficam na mesma phase.
4. O mesmo stage pode aparecer em várias phases não consecutivas.
5. Manter o alvo de aproximadamente sete tasks por phase e teto aproximado de
   dez.
6. Não criar uma divisão artificial que torne uma task não testável ou quebre
   uma cadeia coesa.

Exemplo válido:

```markdown
### Phase 1: Preparação compartilhada
**Stage:** foundation

### Phase 2: API principal
**Stage:** backend

### Phase 3: Interface principal
**Stage:** frontend

### Phase 4: Integração da API
**Stage:** backend

### Phase 5: Documentação
**Stage:** docs
```

O domínio não substitui a modelagem de dependências. Ele adiciona uma
restrição de homogeneidade dentro de cada phase.

Uma task realmente indivisível que mistura dois domínios usa o stage capaz de
executar o conjunto, normalmente `implement`. Se a mistura vier de duas
entregas independentes, a task já viola a regra de atomicidade e deve ser
separada.

### D4 — `foundation`, `backend`, `frontend` e `docs` são exemplos, não nomes fixos

Stages de implementação disponíveis vêm de `.specs/loop.config.toml`.
`implement` sempre existe como fallback. `foundation`, `backend`, `frontend`
e `docs` só podem ser usados quando declarados.

Exemplo:

```toml
[stages.implement]
provider = "claude"
model = "opus"

[stages.foundation]
provider = "codex"
model = "gpt-5.6-luna"
effort = "medium"

[stages.backend]
provider = "codex"
model = "gpt-5.6-luna"
effort = "high"

[stages.frontend]
provider = "cursor"
model = "composer-1"

[stages.docs]
provider = "claude"
model = "haiku"
```

Projetos podem declarar outros nomes, como `mobile`, `infra` ou `data`, desde
que respeitem o formato e não sejam reservados.

### D5 — `verify` e `fix` são reservados

Phase B nunca aceita:

- `verify`
- `fix`
- `continue.respawn`

Esses nomes representam papéis do loop, não domínios de implementação.
`verify` continua sendo um executor novo que não escreveu o código. `fix`
continua separado do Verifier.

### D6 — Fallback só existe para campo ausente

Stage efetivo:

```text
Stage declarado e válido  -> valor declarado
Stage ausente              -> implement, se strict_routing=false
Stage declarado inexistente -> erro sempre
Stage reservado             -> erro sempre
```

Um typo explícito nunca cai silenciosamente em `implement`.

### D7 — Semântica de `strict_routing`

```toml
[execute]
strict_routing = true
```

- `false`, default: uma phase antiga sem `Stage` usa `implement`.
- `true`: toda phase deve declarar `Stage`, inclusive Foundation.
- Stage desconhecido, malformado, duplicado ou reservado é erro nos dois modos.

Quando não existe `[stages.foundation]`, uma Foundation explícita usa:

```markdown
### Phase 1: Preparação compartilhada

**Stage:** implement
```

Assim o modo estrito não entra em conflito com o fallback legítimo.

`strict_routing` deve ser booleano TOML real. Valores como `"false"`, `0` ou
`1` são recusados.

### D8 — Numeração de phase é inteira, positiva e única

Aceito:

```markdown
### Phase 1: Foundation
### Phase 2: Backend
### Phase 3: Frontend
```

Recusado:

```markdown
### Phase 2a: Backend
### Phase 2b: Frontend
### Phase 2: Outro bloco duplicado
```

O parser e o validador de rotas rejeitam o documento. Não preservam a colisão
como comportamento conhecido.

### D9 — Batch homogêneo pelo stage efetivo

`_batching.py` fecha o batch quando a próxima phase possui stage efetivo
diferente. A dobra da cauda de uma ou duas tasks só ocorre quando o stage da
cauda coincide com o stage do batch anterior.

Comparar o stage efetivo preserva compatibilidade:

```text
Phase sem Stage -> implement
Phase sem Stage -> implement
```

As duas ainda podem compartilhar um batch.

### D10 — O detector transporta a decisão

Saída da Phase B:

```text
phase=B action=execute_batch batch=P2 tasks=T4,T5,T6 stage=backend
```

O orquestrador usa exatamente o campo `stage`:

```bash
python3 <skill-dir>/scripts/resolve_stage.py --stage backend ...
```

Nenhum agente recalcula a rota lendo títulos ou configuração por conta própria.

### D11 — O mapa de rotas aparece antes da execução

O bootstrap valida e imprime:

```text
route:
  Phase 1: Preparação compartilhada -> foundation (codex/gpt-5.6-luna)
  Phase 2: API de checkout          -> backend    (codex/gpt-5.6-luna)
  Phase 3: Tela de checkout         -> frontend   (cursor/composer-1)
  Phase 4: Documentação             -> docs       (claude/haiku)
```

Erros são agregados numa única resposta e impedem a criação de `loop.json`.

### D12 — Compatibilidade retroativa

Com `strict_routing=false`, um `tasks.md` antigo sem `Stage` produz:

- os mesmos stages efetivos, todos `implement`;
- os mesmos batches;
- o mesmo dispatch;
- nenhuma mudança em `verify` ou `fix`.

A única diferença permitida é o novo campo `stage=implement` na saída textual
da Phase B. Consumidores e testes precisam ser atualizados para aceitá-lo.

---

## 4. Mudanças de código

### M1 — `scripts/_tasksmd.py`: registros ordenados de phase

Adicionar uma API que devolve phases em ordem documental:

```python
{
    "number": 2,
    "title": "API de checkout",
    "declared_stage": "backend",
    "tasks": ["T4", "T5", "T6"],
}
```

Responsabilidades:

- Capturar número e título completos.
- Capturar `Stage` como primeira linha não vazia depois do cabeçalho.
- Detectar `Stage` duplicado.
- Detectar cabeçalhos não inteiros e números duplicados.
- Continuar expondo por task a phase correspondente.

O mapa não usa apenas `{numero: stage}`. Uma lista ordenada preserva títulos e
permite relatar duplicidades sem sobrescrever dados.

### M2 — `scripts/_routing.py`: única fonte da resolução

Novo módulo puro, importado por bootstrap, detector e validador.

Entrada:

- registros de phase de `_tasksmd.py`;
- config carregada;
- valor de `strict_routing`.

Saída por phase:

```python
{
    "number": 2,
    "title": "API de checkout",
    "declared_stage": "backend",
    "effective_stage": "backend",
    "tasks": ["T4", "T5", "T6"],
}
```

O módulo agrega todos os erros: campo ausente em modo estrito, formato
inválido, stage desconhecido e nome reservado.

### M3 — `scripts/validate_routing.py`: gate antes da aprovação

Novo comando read-only:

```bash
python3 <tlc-loop-dir>/scripts/validate_routing.py <feature> --root <root>
```

Comportamento:

- Lê `tasks.md` e `loop.config.toml`.
- Executa `_routing.py`.
- Imprime o mapa de rotas quando válido.
- Lista todos os erros numa passada.
- Exit `0` para mapa válido, `1` para documento/config inválido, `2` para uso
  incorreto.
- Não cria `loop.json` e não altera arquivos.

O contrato de Tasks manda executar este gate junto com `validate_tasks.py`
antes de apresentar o plano ao usuário.

### M4 — `scripts/_batching.py`: agrupar por stage efetivo

`pack()` recebe phases já resolvidas ou tasks anotadas com `effective_stage`.

Regras:

- Nunca dividir uma phase.
- Preservar ordem documental.
- Fechar por orçamento ou mudança de stage.
- Dobrar cauda de uma ou duas tasks somente com stage igual.
- Incluir `stage` no retorno do batch.

O módulo não lê config e não resolve fallback. Essa responsabilidade fica em
`_routing.py`.

### M5 — `scripts/_config.py`: `execute.strict_routing`

Adicionar default:

```python
"execute": {
    "batch_size": 7,
    "strict_routing": False,
}
```

Adicionar validação de tipo booleano. O leitor existe em `_routing.py` e em
`init_loop.py`, mantendo a regra de que toda chave defaultada possui consumidor.

### M6 — `scripts/init_loop.py`: gate e mapa

Depois de `validate_tasks.py` e do carregamento da config, antes de salvar
estado:

1. Parsear as phases.
2. Resolver as rotas com `_routing.py`.
3. Recusar todos os erros numa única execução.
4. Resolver o harness.
5. Imprimir o mapa com provider/modelo efetivos.
6. Criar `loop.json` somente após todos os gates passarem.

O bootstrap reutiliza a mesma resolução do detector. Não mantém uma segunda
implementação do algoritmo.

### M7 — `scripts/detect_phase.py`: stage no contrato

Ao encontrar tasks pendentes:

1. Recarregar config e `tasks.md`.
2. Resolver phases com `_routing.py`.
3. Empacotar com `_batching.py`.
4. Imprimir `stage=<effective_stage>` na linha da Phase B.

Mudanças em `tasks.md` ou config depois do bootstrap não podem gerar dispatch
silencioso. Um mapa agora inválido faz o detector sair com erro antes de nomear
um batch.

### M8 — `SKILL.md`: dispatch e contrato opt-in de Tasks

Phase B passa de:

```bash
resolve_stage.py --stage implement ...
```

para:

```bash
resolve_stage.py --stage <stage-da-linha-detect> ...
```

Adicionar seção curta:

- Quando `$tlc-loop` é nomeado junto de `$tlc-spec-driven` durante Tasks, ele
  fornece `references/tasks-routing-contract.md` como contrato de saída.
- Ele não assume autoria das Tasks e não inicia Execute.
- O gate `validate_routing.py` é obrigatório antes da aprovação.

### M9 — `references/tasks-routing-contract.md`: handoff entre skills

Novo documento autocontido com:

- formato `**Stage:**`;
- forma curta de invocação;
- descoberta dos stages em `loop.config.toml`;
- stages reservados;
- modo estrito;
- regras de phase homogênea;
- prioridade de dependência e coesão;
- numeração inteira e única;
- comandos `validate_tasks.py` e `validate_routing.py`;
- exemplos válidos e inválidos.

Esse arquivo elimina a necessidade de repetir o contrato inteiro no prompt.

### M10 — documentação operacional

Atualizar:

- `references/config-schema.md`;
- `references/executors.md`;
- `references/phase-transitions.md`;
- `references/checklist.md`;
- `README.md`;
- `assets/loop.config.example.toml`;
- `SKILL.md`.

Remover afirmações de que existem somente três stages. Atualizar exemplos que
fixam `--stage implement` e o vocabulário exato da linha `phase=B`.

---

## 5. Contrato de autoria consumido por `tlc-spec-driven`

Ao receber a forma curta de invocação, o agente mantém o fluxo normal de Tasks
e adiciona estes passos:

1. Ler `.specs/loop.config.toml`.
2. Listar stages de implementação configurados, excluindo `verify` e `fix`.
3. Classificar cada task pelo executor adequado.
4. Desenhar phases homogêneas por stage sem violar dependências.
5. Adicionar `**Stage:**` em cada phase.
6. Usar somente números inteiros, positivos e únicos.
7. Executar o gate normal de Tasks.
8. Executar `validate_routing.py`.
9. Apresentar o mapa de rotas junto com as tasks para aprovação.

Se somente `implement` estiver disponível e o usuário pediu roteamento por
domínio, o agente não inventa `[stages.backend]`. Ele informa que a config não
possui stages de domínio e pede uma destas decisões antes da aprovação:

- configurar stages de domínio;
- manter as phases separadas, mas usar `Stage: implement` em todas;
- abandonar o roteamento para essa feature.

---

## 6. Testes

### Parser e resolução

| Arquivo | Casos obrigatórios |
| --- | --- |
| `test_unit_tasksmd.py` | Stage válido; ausente; duplicado; posição inválida; título livre; `Phase 2a` recusada; número duplicado recusado; layouts plano e aninhado |
| `test_unit_routing.py` | Stage explícito válido; ausente com strict off; ausente com strict on; desconhecido; reservado; vários erros agregados; stages customizados |
| `test_unit_validate_routing.py` | exit codes; mapa válido; todos os ofensores impressos; nenhuma escrita |
| `test_unit_config.py` | default false; true/false válidos; string/número recusados; chave possui leitor |

### Batching e detector

| Arquivo | Casos obrigatórios |
| --- | --- |
| `test_unit_batching.py` | stages diferentes não fundem; stages iguais fundem; cauda só dobra com stage igual; sem Stage mantém batches antigos |
| `test_unit_detect_phase.py` | linha B contém stage; stage acompanha o primeiro batch; avanço troca stage; config inválida impede batch; detector continua read-only |
| `test_unit_resolve_stage.py` | stage de domínio resolve; stage ausente continua erro no resolver; fallback acontece antes, em `_routing.py` |
| `test_unit_init_loop.py` | mapa impresso; strict recusa antes de criar estado; erro agregado; config antiga aceita |

### Integração e documentação

| Arquivo | Casos obrigatórios |
| --- | --- |
| `test_int_end_to_end.py` | Foundation, backend, frontend e docs avançam em batches separados e cada linha carrega o stage correto |
| `test_int_loop_sh.py` | novo campo `stage` não quebra parsing nem terminais E/H |
| `test_unit_docs_parity.py` | halt reasons continuam iguais; novo vocabulário/documentação permanece em paridade |

Regressão principal:

```text
tasks.md sem Stage + strict_routing=false
```

deve produzir exatamente os mesmos agrupamentos e escolher `implement` para
todos os batches.

---

## 7. Ordem de execução e commits

### T1 — Parser de phases e Stage

**Arquivos:** `scripts/_tasksmd.py`, `scripts/test_unit_tasksmd.py`

Entregar registros ordenados, Stage explícito e rejeição de numeração ambígua.

**Gate:** testes unitários de `_tasksmd.py`.

**Commit:** `feat(routing): parse explicit phase stages`

### T2 — Resolução central e config estrita

**Arquivos:** `scripts/_routing.py`, `scripts/_config.py`,
`scripts/test_unit_routing.py`, `scripts/test_unit_config.py`

Entregar stage efetivo, nomes reservados, erros agregados e
`strict_routing` booleano.

**Gate:** testes unitários de routing e config.

**Commit:** `feat(routing): resolve effective implementation stages`

### T3 — Gate read-only de compatibilidade

**Arquivos:** `scripts/validate_routing.py`,
`scripts/test_unit_validate_routing.py`

Entregar validação antes da aprovação sem criar estado.

**Gate:** testes do novo comando.

**Commit:** `feat(routing): add tasks routing validator`

### T4 — Batching homogêneo e detecção

**Arquivos:** `scripts/_batching.py`, `scripts/detect_phase.py`,
`scripts/test_unit_batching.py`, `scripts/test_unit_detect_phase.py`

Entregar batches por stage efetivo e campo `stage` na linha B.

**Gate:** testes unitários de batching e detector.

**Commit:** `feat(routing): emit routed batch stages`

### T5 — Bootstrap e dispatch

**Arquivos:** `scripts/init_loop.py`, `SKILL.md`,
`scripts/test_unit_init_loop.py`, `scripts/test_unit_resolve_stage.py`

Entregar mapa pré-execução, recusa antes do estado e dispatch pelo campo do
detector.

**Gate:** testes unitários de bootstrap e resolver.

**Commit:** `feat(routing): dispatch batches by detected stage`

### T6 — Contrato entre skills e documentação

**Arquivos:** `references/tasks-routing-contract.md`,
`references/config-schema.md`, `references/executors.md`,
`references/phase-transitions.md`, `references/checklist.md`, `README.md`,
`assets/loop.config.example.toml`, `scripts/test_unit_docs_parity.py`

Entregar a forma curta de invocação e todos os contratos públicos atualizados.

**Gate:** testes de paridade documental e suíte unitária completa.

**Commit:** `docs(routing): define staged tasks handoff`

### T7 — Regressão end-to-end

**Arquivos:** `scripts/test_int_end_to_end.py`,
`scripts/test_int_loop_sh.py`

Provar o fluxo completo por quatro stages e a compatibilidade com tasks antigas.

**Gate:** suíte unitária e de integração completa.

**Commit:** `test(routing): cover staged loop execution`

---

## 8. Riscos e mitigação

| Risco | Mitigação |
| --- | --- |
| Usuário invoca apenas `$tlc-spec-driven` | Integração é opt-in e documentada; tasks antigas continuam válidas |
| Stage digitado errado | Stage explícito desconhecido é erro, nunca fallback |
| Foundation não possui stage próprio | Usar `Stage: implement` ou configurar `[stages.foundation]` |
| Phases demais por domínio | Dependência e coesão vêm primeiro; medir batches da primeira feature real |
| Um domínio reaparece depois de outro | Permitido; stages podem se repetir em phases não consecutivas |
| Config muda após bootstrap | Detector recalcula com a mesma `_routing.py` antes de cada batch |
| `verify` ou `fix` usados por engano | Nomes reservados são recusados em todos os modos |
| Consumidor depende da linha B antiga | Atualizar contratos, testes unitários e integração no mesmo rollout |

---

## 9. Critérios de aceite do plano

- A forma curta com `$tlc-spec-driven` e `$tlc-loop` possui significado
  completo sem regras repetidas no prompt.
- Títulos de phase não controlam roteamento.
- Toda rota usada no dispatch aparece como `stage=` na linha do detector.
- Batches são homogêneos pelo stage efetivo.
- `strict_routing=true` funciona com Foundation explícita.
- Stages desconhecidos e reservados nunca caem em fallback.
- `Phase 2a`, `Phase 2b` e números duplicados são recusados.
- `verify` e `fix` mantêm seus papéis atuais.
- Tasks antigas sem Stage continuam executando em `implement` com os mesmos
  batches quando o modo estrito está desligado.
- Nenhuma mudança em `tlc-spec-driven` é necessária para o modo opt-in.
