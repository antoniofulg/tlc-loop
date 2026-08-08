# Contexto: tlc-loop-tasks

Registro das decisões tomadas na fase de discussão. Cada entrada traz a decisão,
o motivo, as alternativas descartadas e — quando aplicável — a evidência que a
sustenta. Escrito em português porque é o registro da conversa; `spec.md` fica em
inglês por exigência do `validate_spec.py`.

---

## Origem

Adaptação do skill `cy-loop-tasks` (Compozy,
`.agents/skills/cy-loop-tasks`) para o ecossistema do `tlc-spec-driven`.

**O que o `cy-loop-tasks` traz que o `tlc-spec-driven` não tem:**

| Lacuna | `cy-loop-tasks` | `tlc-spec-driven` hoje |
| --- | --- | --- |
| Detecção de fase determinística | `detect-phase.py` deriva a próxima ação de estado + filesystem | resume é reconciliação conduzida pelo modelo (`memory.md`) |
| Estado machine-owned | `state.yaml`, escritor único, log append-only capado em 50 | `STATE.md` em markdown escrito pelo modelo |
| Recovery loop + teste de bloqueio externo | `recovery-loop.md`: falha é reparável por padrão; 3 critérios provados para `blocked` | não existe |
| Checkpoint commit atômico | `commit-checkpoint.py` captura código + memória + estado num snapshot | commit por disciplina do modelo; `check_commit.py` valida só formato |
| Continue gate | loop re-entra em detect na mesma volta até a fase terminal | agente para ao fim de cada resposta |

**O que foi descartado por acoplamento ao Compozy:** `.compozy/tasks/<slug>/`,
`_techspec.md`, `herdr` / `rtk herdr agent start`, skills `cy-*`
(`cy-execute-task`, `cy-final-verify`, `cy-workflow-memory`,
`cy-spec-preflight`), `qa-report` / `qa-execution` + `docs/qa/`,
`deep-review --subagent codex`, `make gate` / `make gate-full`, `gh stack`, e o
`done-signature` amarrado ao `codex-loop-plugin`.

---

## Decisões

### D1 — Skill irmão, não fork nem fold-in

**Decisão.** Criar `tlc-loop-tasks` como skill separado que dirige o
`tlc-spec-driven` sem substituí-lo, mais um gancho pequeno no `implement.md`
transformando a oferta atual (inline vs sub-agents) numa escolha de três vias:
inline / sub-agents / loop.

**Por quê.** O `tlc-spec-driven` faz auto-sizing: features Small pulam Design e
Tasks inteiros. Embutir uma máquina de estados obrigatória dentro do Execute
penaliza justamente o caminho leve, que é a maioria dos casos.

**Alternativas descartadas.** Fold-in (engorda o SKILL.md e onera Small/Medium);
skill irmão zero-touch (o loop nunca seria sugerido no momento certo, só quando
o usuário lembrasse de pedir).

---

### D2 — Escopo: Execute + Validate; Fase C (QA) dropada

**Decisão.** O loop cobre apenas Execute e Validate. Specify, Design e Tasks
continuam interativos. A Fase C (QA) do `cy-loop-tasks` não é portada.

**Por quê.** Specify/Design/Tasks são onde a revisão humana rende mais — são
decisões difíceis de reverter. A Fase C depende das skills `qa-report` e
`qa-execution` do Compozy, que não existem aqui; o Verifier do `tlc-spec-driven`
(spec-anchored check + discrimination sensor) já é o portão de qualidade.

---

### D3 — Verdade do status: git trailer

**Decisão.** O commit atômico de cada task carrega trailers:

```
feat(auth): add token refresh service

Task: T3
Gate: quick PASS
```

`detect_phase.py` deriva as tasks concluídas de
`git log --format="%(trailers:key=Task,valueonly)"`. O `loop.json` é cache
reconstituível, não fonte de verdade.

**Por quê.** O `tasks.md` do `tlc-spec-driven` **não tem campo de status** — os
`- [ ]` ficam sob "Done when" e são critérios de aceitação, não estado da task.
O `validate_tasks.py` parseia `### T1:`, `Depends on`, `Where`, `Tests` e
`Gate`; status não aparece. Ou seja, "Mark the task complete in `tasks.md`"
(`implement.md` step 7.1) é hoje indefinido e o modelo improvisa.

O trailer resolve sem inventar formato: o registro fica no commit que o
`tlc-spec-driven` já obriga a existir; ninguém escreve no arquivo autoral;
sobrevive a rebase e cherry-pick; e imuniza contra edição manual do `tasks.md`.
Também dissolve a tensão interna do tlc, em que `sub-agents.md` manda o
orquestrador atualizar o `tasks.md` por batch enquanto os commits acontecem por
task.

**Evidência (verificada localmente, git 2.50.1).** Escrita via
`git commit --trailer "Task: T3"`; leitura estruturada retornou apenas as tasks
reais, ignorando commits sem trailer. `check_commit.py` aceitou a mensagem com
trailer sem alteração (`check_commit: OK`, exit 0) — ele valida só o cabeçalho
(`HEADER_RE`) e a regra de `BREAKING CHANGE:`.

**Precisão importante.** O trailer é **registro**, não prova. Quem prova é o
gate (exit code do test runner) e, no fim, o Verifier. A ordem é rígida: gate
verde primeiro, commit com trailer depois.

**Alternativas descartadas.** Marcador HTML no `tasks.md` (o loop passa a
escrever num arquivo que o humano também edita); sidecar `tasks.state.yaml`
(vira fonte única sem nada contra o que reconciliar); um arquivo por task ao
estilo `task_NN.md` (quebra `validate_tasks.py` e o formato de features
existentes).

---

### D4 — Fase B: batches de ~7 do tlc

**Decisão.** Manter o modelo do `tlc-spec-driven`: batches de ~7 tasks por
worker, fases inteiras, workers sequenciais, commit atômico **por task** dentro
do worker.

**Por quê.** As duas abordagens resolvem eixos diferentes: o batching do tlc
resolve orçamento de contexto (`<40k tokens` na janela principal); a
task-por-iteração do cy resolve granularidade de recuperação. Com o trailer do
git (D3) como verdade, não há escrituração para atrasar — o commit é o registro,
escrito no instante em que a task fecha. Batching deixa de custar granularidade
de restore, e ficamos com as duas propriedades.

**Correção registrada.** Uma análise anterior afirmou que um crash no meio de um
batch perderia até 7 tasks. Está errado: o worker faz
`implement → gate → commit atômico` para cada task (`implement.md:29`). O batch
é unidade de despacho, não de commit; um crash perde só a task em voo.

**Acoplamento.** Esta decisão depende de D3. Com marcador HTML em vez de
trailer, batching voltaria a custar granularidade.

---

### D5 — Verify: author ≠ verifier preservado

**Decisão.** A Fase D do `cy-loop-tasks` vira **duas** fases:

```
V-verify  → subagente fresco, read-only, escreve validation.md
V-fix     → implementador separado, consome os gaps ranqueados
            ↑                                    ↓
            └──────── N voltas (config) ─────────┘
                            ↓ (esgotou)
                     escala para o usuário
```

**Por quê.** O `cy-loop-tasks` colapsa as duas coisas — *"The loop is the
deciding authority over the round: remediate every confirmed finding and every
nitpick from the round's review.md in this same iteration"*. O
`tlc-spec-driven` mantém o Verifier estritamente read-only
(*"Does NOT write, modify, or fix any code or tests"*) e roteia os gaps a um
implementador separado. Esse é o portão author ≠ verifier; colapsá-lo destrói a
confiabilidade da validação.

Decisão do usuário: manter a abordagem do tlc mesmo custando uma ida e volta de
agente a mais por rodada.

**Limite de rodadas.** O tlc fixa 3 (`sub-agents.md:122`). Aqui vira
configurável, sem teto hardcoded — decisão explícita do usuário.

---

### D6 — Config: `provider` / `model` / `effort` por stage

**Decisão.** `.specs/loop.config.toml`, versionado, lido e nunca escrito pelo
loop:

```yaml
stages:
  implement: { provider: codex,  model: gpt-5.6-luna, effort: max }
  verify:    { provider: claude, model: opus,         effort: high }
  fix:       { provider: codex,  model: gpt-5.6-luna, effort: max }
```

Acompanhado de `references/providers.md` com a tradução de cada provider para
linha de comando.

**Por quê.** O `tlc-spec-driven` já tem uma tabela "Model Tier per Role" em
`sub-agents.md`, mas ela é prosa consultiva (*"Applies only if the harness can
assign a model per sub-agent"*). Virar config torna a intenção executável.

**A tabela de adapter é obrigatória**, porque os três providers expressam
modelo+effort de formas incompatíveis (verificado nos CLIs instalados):

| Provider | Modelo | Effort |
| --- | --- | --- |
| `claude` | campo separado | campo separado |
| `codex` | `-m` | `-c model_reasoning_effort=` |
| `cursor` | `--model` | **embutido no nome do modelo** (`gpt-5.6-sol-xhigh`) ou sintaxe de colchete `'claude-opus-4-8[effort=high]'` |

Sem a tabela, o modelo improvisaria a linha de comando e erraria.

**Correção de enum.** `effort: ultra` não existe em nenhum dos três. Valores
suportados: `low | medium | high | xhigh | max`. O adapter deve rejeitar valor
não suportado pelo provider alvo em vez de mandar e falhar silencioso.

**Separação config/estado.** Dois arquivos, nunca um. Config é do usuário,
versionada, o loop só lê. `loop.json` é do loop, machine-owned, o usuário nunca
toca. O `cy-loop-tasks` leva isso a sério: *"`state.yaml` mutates only through
`init-state.py` and `update-state.py`; hand-edits void resume guarantees."*

---

### D7 — Executores abstraídos: sem amarra no herdr

**Decisão.** Duas espécies de executor:

- `kind: agent` — mecanismo nativo de subagente do orquestrador. Sem
  subprocesso, contexto compartilhado, barato. Só modelos do próprio harness.
- `kind: command` — comando de shell. Qualquer CLI (`codex`, `cursor-agent`,
  `claude -p`, e `rtk herdr` se o usuário quiser).

**Por quê.** O herdr é apenas um despachante — lança um agente, entrega contexto,
espera, lê evidência. O `cy-loop-tasks` amarrou o conceito ao produto. Abstraído,
o herdr vira uma linha de config opcional em vez de dependência.

**Restrição honesta.** A Agent tool nativa do Claude Code só despacha modelos
Claude. Rodar GPT/Grok/Kimi exige executor `command` — não há como contornar
isso de dentro do Claude Code.

**Duas regras que valem para qualquer executor**, herdadas do cy:

1. **Executor nunca commita.** O loop commita. Sem isso, um agente externo cria
   commits fora do padrão de trailer e o `detect_phase` se perde.
2. **Evidência é verificada, não confiada.** O loop confere que os artefatos
   prometidos existem e que o gate passou, antes de avançar estado.

**Custo do `command`.** Contexto zero (payload completo por arquivo),
observabilidade limitada ao que o processo escrever em disco. Exige um
`references/executors.md` — o equivalente agnóstico do `herdr-delegation.md`.

**Nomear o provider, não "native".** `provider: claude` é portátil; `native` é
relativo a quem orquestra e quebra ao trocar de agente. A resolução acontece em
runtime: se o `provider` for igual ao orquestrador rodando, usa o mecanismo
nativo; senão, sobe o CLI.

---

### D8 — Condições de parada

**Decisão.** Oito, nenhuma delas tratada como falha — todas escrevem estado e
param limpo para retomada.

*Terminais de sucesso*
1. Fase terminal — `validate_state.py` exit 0

*Terminais de escalação*
2. Bloqueio externo provado (3 critérios do `recovery-loop`)
3. Rodadas de verify esgotadas sem PASS
4. Operação de blast radius (push / deploy / migração) — já é regra do tlc

*Detectores de runaway*
5. Sem progresso: N iterações sem commit novo
6. Gate falhando repetidamente na mesma task
7. Falha de executor: CLI ausente, auth expirada, quota estourada

*Disjuntor global*
8. `max_iterations` e/ou `max_minutes`, ambos aceitando `null` = infinito

**Por quê.** 5 e 6 são os que realmente pegam runaway. Sem o detector de
não-progresso, um loop quebrado gira a noite inteira parecendo saudável. O 7
atende diretamente o cenário de troca de provider por falta de token.

**Decisão explícita do usuário.** Sem teto hardcoded em nenhum limite; tudo fica
a cargo de quem configura.

---

### D9 — Continuação: in-turn + `/goal` + `loop.sh`

**Decisão.**

```yaml
continue:
  in_turn: true       # motor — sem pausa enquanto o turno vive
  mode: auto          # auto | goal | shell | none
  respawn:            # lido quando mode resolve para shell
    provider: auto
    model: opus
    effort: high
```

`mode: auto` resolve por harness: **`/goal`** no Claude Code, **goal nativo** no
codex, **`loop.sh`** no cursor ou em qualquer outro CLI.

**Por quê.** Um agente para quando termina a resposta. O in-turn encadeia
batches sem pausa enquanto o turno vive; os outros mecanismos existem para o
turno morrer.

**Descoberta que definiu o desenho.** O `/goal` do Claude Code (v2.1.139+;
documentado em `code.claude.com/docs/en/goal`) não é o `/loop` com outro nome:

| Abordagem | Próximo turno começa quando | Para quando |
| --- | --- | --- |
| `/goal` | **o turno anterior termina** | um modelo confirma a condição |
| `/loop` | um intervalo de tempo passa | usuário para, ou o modelo julga terminado |
| Stop hook | o turno anterior termina | script próprio decide |

`/goal` tem tempo morto zero, juiz independente (*"completion is decided by a
fresh model rather than the one doing the work"* — mesmo princípio do
author ≠ verifier), roda não-interativo via `claude -p "/goal ..."` e é
restaurado com `--resume`/`--continue`.

O codex tem feature equivalente nativa, confirmada em `~/.codex/goals_1.sqlite`:
tabela `thread_goals` com `objective`, `token_budget`, `tokens_used`,
`time_used_seconds` e status `active|paused|blocked|usage_limited|budget_limited|complete`.

**Por que o `loop.sh` fica mesmo assim.** Cobre CLIs sem mecanismo de goal — o
cursor, hoje. Como executor de `implement`/`fix` o cursor não precisaria dele;
como orquestrador, precisaria.

**Correção registrada.** Uma análise anterior afirmou que `/goal` não existia no
Claude Code, baseada em busca no filesystem (`~/.claude/commands/`). Instrumento
errado: comandos nativos não são arquivos em disco.

**Descartado.** `/loop` como rede — é baseado em intervalo (mínimo 60s por
volta), o que o desqualifica frente ao `/goal`. Dependência do
`codex-loop-plugin`, que não está instalado em lugar nenhum da máquina.

---

### D10 — `respawn.provider: auto`

**Decisão.** Valor padrão `auto`: detecta o harness em runtime **no bootstrap**,
grava o resolvido no `loop.json` (estado), e nunca reescreve a config. Valor
explícito sempre vence.

**Por quê.** Detectar é grátis — confirmado nesta sessão: `CLAUDECODE=1`,
`CLAUDE_CODE_ENTRYPOINT=cli`, e de brinde `CLAUDE_EFFORT=xhigh`. Escrever na
config é que sai caro: apaga a separação config/estado, suja o `git diff` a cada
sessão, e destrói a intenção do usuário (que setou `codex` de propósito por falta
de token).

**Resolve uma vez, não a cada volta.** Sem isso, um run trocaria de agente no
meio sem avisar — metade das tasks implementada por um modelo, metade por outro.

**Lacuna conhecida.** Só o marcador do Claude Code foi verificado. Os
equivalentes de `codex` e `cursor-agent` exigem uma sondagem dentro de cada um.
Se a detecção falhar, o loop **não chuta**: para e pergunta.

---

### D11 — Done-signature

**Decisão.** Após `validate_state.py` sair 0, o loop imprime uma linha literal
de assinatura no transcript.

**Por quê.** É a interface com qualquer avaliador. A doc do `/goal` é explícita:
*"The evaluator judges your condition against what Claude has surfaced in the
conversation. **It doesn't run commands or read files independently.**"* O
avaliador não roda `validate_state.py`; ele lê o transcript.

Isso explica a `done-signature` do `cy-loop-tasks`
(`__CY_LOOP_TASKS__ phase=E qa=COMPLETE review=SHIP verify=PASS`): não é
resquício de plugin, é o contrato com o avaliador. Uma linha serve os três
mecanismos — o Haiku do `/goal`, o goal nativo do codex e um `grep` no
`loop.sh`.

---

### D12 — `objective` read-only e status

**Decisão.** `loop.json` guarda o `objective` verbatim, imutável após o
bootstrap, mais status e contadores de tempo/iterações. Vocabulário de status
copiado do schema do codex: `active | blocked | halted | complete`.

**Por quê.** Impede o loop de redefinir o próprio critério de sucesso no meio do
caminho — o `cy-loop-tasks` faz o mesmo com `goal_signature` (*"Read-only after
bootstrap"*).

**O que não construímos.** Contagem de token. Nem o Claude Code nem um script
nosso expõem isso de forma confiável a partir da skill; `/goal` mostra no status
e o codex guarda no sqlite. Leitura oportunista, nunca implementação própria.

---

### D13 — Formatos: config em TOML, estado em JSON

**Decisão.** `.specs/loop.config.toml` lido com `tomllib` (stdlib desde 3.11);
`.specs/features/<f>/loop.json` lido e escrito com `json` (stdlib).

**Por quê.** A regra de zero dependência descartou PyYAML, e a alternativa era
escrever um leitor de subconjunto YAML **mais** um emissor — o componente mais
arriscado do design inteiro, sem ganho visível para quem usa. `tomllib` resolve a
config sem uma linha de parser nossa, e TOML já é o formato do seu
`~/.codex/config.toml`. JSON resolve o estado pelo mesmo motivo.

**Custo aceito.** TOML não tem `null`; chave de limite omitida significa
ilimitado.

**Descoberto durante o planejamento de tasks**, não na discussão — é o tipo de
simplificação que só aparece ao enumerar o trabalho real.

---

## Pendências de verificação

Não são suposições resolvidas — são coisas a confirmar antes ou durante a
implementação:

1. Marcadores de ambiente do `codex` e do `cursor-agent` (só o do Claude Code
   foi verificado).
2. Se o `cursor-agent` tem algum mecanismo de continuação nativo. Assumimos que
   não; se tiver, entra no `mode: auto`.
3. Formato exato da condição de `/goal` que ancora na done-signature, testado na
   prática com o avaliador.
4. Comportamento de tasks sem diff (config-only): resolvido no design com a lista
   `no_diff_tasks` no `loop.json`, unida aos trailers do git. Falta confirmar na
   implementação que a união não gera falso positivo após rebase.

## Ideias adiadas

- `implement.mechanical` como override separado de `implement`, espelhando a
  distinção core-domain vs mechanical da tabela de tiers do `sub-agents.md`.
- Stop hook com script como quarta via de continuação — mais determinístico que
  o avaliador-modelo do `/goal`, mas mora no `settings.json` em vez de ser por
  sessão.
- Suporte a `--stacked` / stacked PRs (`gh stack`), presente no `cy-loop-tasks` e
  fora do escopo aqui.
