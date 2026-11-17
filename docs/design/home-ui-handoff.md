# HANDOFF — iTV Home (patch 0002)

Para: thread principal (Sol), que instala na TV.
De: thread de implementação da Home, 2026-11-16.
Fonte da verdade do comportamento: `docs/design/home-ui.md`.

Este pacote **não** foi integrado ao repositório iTV e nada foi feito na TV. O usuário entrega este diretório.

## Conteúdo do pacote

| Arquivo | O que é |
| --- | --- |
| `0002-itv-home-ui.patch` | Patch único: `git diff` de `pinado 8ec9513 + 0001` até o código final. SHA-256 `805dd360fa3caa1d99300905585d343e8556a3e04d343a24c0a301c955bc6579`. |
| `screenshots/*.png` | 31 capturas 1920×1080 do build de produção no Chromium (ver lista abaixo). `00-prototype.png` é o protótipo aprovado, para comparação. |
| `test-output/*.log` | Saída das checagens upstream, dos specs de navegador e o diffstat. |

## Rodada 8 — fade de volta mais lento (2026-11-17)

**Retorno do usuário:** o fade de volta funcionou, mas ficou "meio rápido demais".

**Mudanças:**
- `--motion-duration-itv-reveal` passou de 0,5 s para **0,8 s**. A mesma duração vale para o tile do app encolhendo.
- A curva da cortina passou a ser `cubic-bezier(0.25, 0.1, 0.25, 1)`: clareia mais no começo e assenta devagar.
- A espera de 450 ms antes do fade continua igual.

## Rodada 7 — volta para a Home visível (2026-11-17)

**Retorno do usuário:** a animação de abrir está boa. Ao apertar Home, porém, a tela fica preta de forma abrupta por ~0,5 s e a Home aparece pronta, sem animação.

**Causa provável:** ao apertar Home, a TV faz a própria transição preta (~0,5 s), e a página já se declara visível no início dela. O fade da rodada 6 começava dois quadros depois disso e terminava antes de a TV mostrar a página.

**Mudança:**
- O fade espera `RETURN_REVEAL_DELAY_MS = 450` (em `launcher/src/itv/index.tsx`) e mais dois quadros, e passa a durar 0,5 s.
- O preto da TV emenda no preto da nossa cortina, e a Home surge do escuro com o tile do app encolhendo.
- Uma tecla apertada durante a espera devolve a Home na hora.
- Se o app foi aberto pelo botão do controle, a última imagem é a própria Home, e a volta continua sem fade.

**Ajuste na TV:**
- Se o fade ainda não aparecer, aumentar `RETURN_REVEAL_DELAY_MS` (por exemplo, 600–700).
- Se a espera no preto ficar longa demais, diminuir.

## Rodada 6 — novo layout e volta para a Home (2026-11-17)

**Retorno do usuário na TV:** o atraso sumiu, o som está sincronizado e a animação de abrir app aprovada. A volta para a Home mostrava preto e depois a Home "estalava". O Settings do tile não abria nada.

**Decisões do usuário** (grill desta rodada, com o protótipo A/B em `.cache/home-ui-dev/layout-mock-inline.html`):
1. **Sem tile Settings.** O menu da Samsung abre pelo botão do controle. Tematizar esse menu não é possível sem root; existem só "Menu Style" (tamanho/transparência) e High Contrast na própria TV. Por isso o Settings foi removido também do upstream: não há mais `openSettings`, `SETTINGS_APP_IDS` nem a descoberta de IDs. Das edições fora do módulo sobra só o callback de falha em `launch`/`openStore`.
2. **Grade ancorada embaixo:** a última linha visível fica a 60 px da borda inferior (y = 870) e as linhas crescem para cima. Com duas linhas, a linha 1 fica em y = 634.
3. **Placa de vidro única e contínua** atrás de todas as linhas visíveis, inclusive da linha do Apps revelada. Ela cresce abaixo da tela antes de a grade subir e só encolhe depois de a grade descer, sem animar a altura.
4. **Ordem:** seus apps, os apps novos e o PS4 preenchem em ordem; o PS4 entra numa vaga da linha 1, se houver.
5. **Tile Apps escondido** numa linha própria abaixo da grade, na coluna 1:
   - ↓ em qualquer coluna da última linha faz a grade subir uma linha e foca o Apps;
   - ↑ volta para o tile de onde veio;
   - ←, → e ↓ no Apps dão bump;
   - segurar OK mostra "Apps has a fixed place".
6. **Volta para a Home, espelhando a abertura:** o fade a partir do preto passou a 0,4 s e só começa dois quadros depois de a página reaparecer, quando a TV já está desenhando; antes ele podia terminar antes do primeiro quadro, e a Home "estalava". Durante o fade, o tile do app encolhe de 1,06 para o normal.
7. **Menu de segurar OK** abre **acima** do tile, na área livre, sem cobrir a linha de baixo.

Novas capturas:
- `02-home-first-run`: duas linhas ancoradas;
- `85-apps-reveal-170ms` e `86-apps-revealed`;
- `87-one-row-apps-revealed`;
- `30`/`31`: menu acima do tile.

## Rodada 5 — resposta imediata às setas (2026-11-17)

**Retorno do usuário:** navegação "super laggy", com toques rápidos "pulando" apps. O som pareceu mudar depois de um reinício. O brilho a cada tile é repetitivo.

**Diagnóstico** (Fable, com base no código e na arquitetura do Chromium M120; não medido na TV):
- O JS e o re-render não são o gargalo: ~1–2 ms por tecla, e a tecla chega em 2–11 ms.
- O custo provável está na TV: a cada foco, camadas de composição são criadas e destruídas (elevação, sombra, brilho), e o fundo é invalidado.
- No modo mover, os tiles eram reinseridos no DOM a cada troca, o que reinicia animações e recria camadas.
- "Engole e pula" é a thread principal bloqueada no commit esperando o raster anterior.

**Mudanças:**
1. Os tiles têm **ordem fixa no DOM** (por chave) e são posicionados só por transform. No modo mover, eles deslizam em vez de serem recriados.
2. **Camadas estáveis:**
   - `will-change: transform` em todo `.lift`. A nitidez do logo focado foi conferida e ficou idêntica.
   - `will-change` na sombra e no brilho, só no tile focado.
   - `will-change: transform` na grade inteira, para não invalidar o wallpaper.
3. **Brilho só ocasional:** aparece no primeiro movimento depois de 2,5 min sem navegar (ou no primeiro após ligar), a pedido do usuário.
4. **Modo rápido:** com setas a menos de 160 ms uma da outra, o foco muda sem animação, e a animação volta 260 ms depois da última seta. Cada toque continua contado e com som.
5. **Som:** a Home **sempre inicia no Feltro**. O modo Samsung (Back segurado 1,5 s) vale só até o próximo reinício. Antes ele ficava gravado, o que provavelmente explica o "som mudou" depois do reinício do diagnóstico.
6. **Medição:**
   - `itvPerf.presented()` traz o Event Timing do próprio navegador para keydowns acima de 16 ms: `presentedMs` mede do evento até o quadro pintado, `queuedMs` mede a espera até o handler.
   - Junto com `itvPerf.report()`, mostra se ainda há fila.

**No Mac** (CPU 6× mais lenta): o quadro sai em 16–24 ms, tanto com setas espaçadas quanto com setas a cada 60 ms. O Mac não reproduz o raster da TV.

## Rodada 4 — Settings, diagnóstico na TV e fluidez (2026-11-17)

**Diagnóstico feito pela thread principal (só leitura):**
- `app_launcher --list` encontrou o Settings da Samsung: `com.samsung.tv.coba.setting` (nome "Setting").
- O inspect funcionou. `itvAudio.report()` mostrou a tecla chegando à página em 2–11 ms. O áudio do navegador tem latência informada de 50 + 50 ms e estima 48–96 ms até a primeira amostra sair.
- O trace de performance não foi capturado.

**Mudanças:**
1. **Settings:**
   - `SETTINGS_APP_IDS` agora é `["com.samsung.tv.coba.setting", "org.tizen.menu"]`.
   - A descoberta automática só aceita IDs que **terminam** em `setting`/`settings`, o que exclui sub-telas e apps de sistema sem tela, como `health-mde-setting`. A causa provável da tela preta era o launcher abrir um desses.
   - O Settings **não usa a cortina preta**: ele abre como painel por cima da Home.
2. **Fluidez da navegação:**
   - O `Tile` é memoizado, então um movimento de foco re-renderiza só os dois tiles afetados.
   - A sombra do foco, antes um box-shadow com blur de 60 px, passou a ser um bitmap pré-desenhado (`createFocusShadow.ts`) que só aparece por opacidade.
   - No Mac, com a CPU 6× mais lenta, o handler leva ~1 ms e o quadro sai em ~26 ms. Com a tecla chegando em ~5 ms na TV, o atraso visível deve estar na rasterização e na composição da TV.
3. **Medição:** `itvPerf.report()`, via inspect, lista as últimas 60 teclas com:
   - `queuedMs`: do evento até o handler;
   - `handlerMs`: o trabalho do handler;
   - `frameMs`: do handler até o quadro pintado, medido com dois `requestAnimationFrame`.

   O `frameMs` é o número que separa nosso código do desenho na TV.

## Rodada 3 — som escolhido e A/B com os beeps da Samsung (2026-11-17)

1. **Sons:** o usuário ouviu um laboratório no Mac (`.cache/home-ui-dev/sound-lab.html`) e escolheu o conjunto **"Feltro"**: toques graves e macios, quase sem clique, com um baque macio na borda. Ele **substitui** os cliques da rodada 2 e o Soft/Wood/Pebble da spec.
   - Valores em `launcher/src/itv/sounds/createItvSounds.ts`.
   - **Atualize `docs/design/home-ui.md` (seção Sounds)** no repositório: a thread de implementação não edita a árvore principal.
2. **A/B de latência com os beeps nativos da Samsung** (pedido do usuário):
   - O app pode tocar os beeps de interface da própria TV por `tizen.tvaudiocontrol.playSound`. Eles saem pelo áudio do sistema, não pelo do navegador.
   - Para isso, o `launcher/config.xml` ganhou **uma linha**: `<tizen:privilege name="http://tizen.org/privilege/tv.audio"/>`. É a única mudança no `config.xml`; identidades, serviço e Native Home seguem iguais.
   - Esse privilégio deve ser de nível público, compatível com o certificado de autor que a CLI usa. **Confirme que a instalação aceita.** Se for recusada por privilégio, remova essa linha e o modo Samsung só mostrará "Samsung sounds are unavailable on this TV".
   - **Como alternar na TV:** segurar **Back por 1,5 s** na Home. Aparece "Sounds: Samsung" ou "Sounds: iTV", e a escolha fica gravada (`localStorage["itv.sounds.v1"]`).
   - Esse gesto é **temporário**, só para o A/B. Remover depois que o usuário decidir.
   - Mapeamento dos beeps: move → MOVE, OK e menu → SELECT, Back → BACK, borda → WARNING.

## Rodada 2 — feedback do primeiro teste na TV (2026-11-16)

O usuário instalou a primeira versão. Os relatos e o que mudou:

1. **"Settings não abre."** Os IDs eram palpites. Agora `openSettings` tenta, nesta ordem:
   - apps instalados cujo **nome** é "Settings" (ou Configurações, Ajustes etc.);
   - apps cujo **ID** contém `settings`;
   - os palpites de `SETTINGS_APP_IDS`;
   - a requisição padrão do Tizen `http://tizen.org/appcontrol/operation/setting`, sem app fixo.

   A busca usa o inventário completo do `getAppsInfo()`, inclusive apps de sistema (`settingsCandidates` em `services/createAppsService.ts`, com teste). **Se ainda não abrir:** rode `aerotizen --tv <IP> apps --raw` (só leitura), ache a linha do app de Configurações da Samsung e ponha o ID no início de `SETTINGS_APP_IDS` em `launcherConfig.ts`.
2. **"O som não ficou bom."** (Substituído na rodada 3 pelo conjunto Feltro.) Nesta rodada eram cliques curtos e secos, no estilo de interface de TV, sem cauda tonal e sem reverb:
   - move: tique agudo e leve;
   - OK: clique firme;
   - Back: o mesmo clique, mais grave;
   - borda: batida abafada;
   - menu: clique que sobe.

   Isto **substitui** os sons Soft/Wood/Pebble que a spec aprovou. O usuário pediu para "ficar com o tradicional de TV" e deixou a escolha conosco. A spec (`docs/design/home-ui.md`, seção Sounds) deve ser atualizada se ele aprovar na TV.
3. **"O som tem delay."** Investigação feita (Fable): não há atraso proposital no código, mas havia três atrasos nossos, todos corrigidos:
   - o som do OK só tocava ao **soltar** o botão; agora toca ao apertar;
   - a primeira tecla criava todo o áudio; agora o contexto nasce com a Home e é retomado a cada volta;
   - o Chromium suspende a saída de áudio após ~30 s de silêncio total e o primeiro som seguinte atrasa. Agora um ruído inaudível (cerca de −80 dBFS) mantém a saída ativa enquanto a Home está visível. O contexto é suspenso ao sair, para não segurar o áudio sob outros apps.

   Além disso, os sons são pré-renderizados uma vez (`OfflineAudioContext`), e cada tecla só dispara um buffer pronto. O resto do atraso deve vir do pipeline de áudio da TV, fora do nosso controle (ver checklist).
4. **"Ao abrir um app a tela só trava."** Agora há uma transição:
   - no OK, o tile cresce (×1,06) e a tela escurece até o preto em 220 ms;
   - o app é lançado por trás do preto, e o carregamento acontece numa tela preta limpa;
   - na falha, a Home volta (bump + "Couldn’t open X");
   - se nada cobrir a Home em 6 s, ou se o usuário apertar uma tecla, a Home volta.

   Isso soma 220 ms ao início do lançamento; com o modo de performance, a duração vai a 0.
5. **"Ao voltar com Home há um zoom temporário e depois zoom out."** Causa: ao esconder, a Home tirava o foco visual do tile. A TV mostrava o quadro antigo e depois animava o tile "desfocando" e "refocando". Agora o visual do foco não muda ao esconder. Quando a volta é de algo aberto pela Home, ela reaparece a partir do preto (fade de 300 ms), já com o foco parado no app.

Novas capturas: `90-open-110ms`, `91-open-covered`, `92-return-120ms`, `93-return-done` (a dica "Would open Netflix" só existe no navegador, sem TV).

### Como medir o atraso do som na TV

1. Na TV, navegue pela Home por uns 20 toques (incluindo um após ficar mais de 30 s parado).
2. No Mac: `aerotizen --tv <IP> inspect launcher` e, no console do DevTools, `itvAudio.report()`. Cada linha traz:
   - `sound`;
   - `keyAgeMs`: do evento de tecla até o som começar na página;
   - `etaMs`: quanto o motor estima até a primeira amostra sair;
   - `baseLatencyMs` e `outputLatencyMs`;
   - `state`;
   - `idleMs`: tempo desde o som anterior.
3. Faça também a medição física: grave com o celular o clique do botão do controle e o som da TV e meça o intervalo na forma de onda. Repita com o beep nativo dos menus da Samsung ("Sound Feedback" ligado).
4. Como ler:
   - `etaMs`/`baseLatencyMs` altos (80 ms ou mais): o buffer do motor domina;
   - valores baixos com atraso físico alto: o atraso é da TV ou do dispositivo de saída;
   - `keyAgeMs` alto: thread principal ocupada.

## O que mudou e por quê

### Módulo novo: `launcher/src/itv/`

A Home do AeroTizen foi substituída por um módulo novo e coeso, montado pelo mesmo contrato de view (`LauncherViews.home` → `MountedView<HomeBridge>`). Assim, composição do app, escopos de input, boot, Settings e hot reload continuam os do upstream. A Home antiga (`launcher/src/home/`) ficou no código, sem uso, para o patch continuar pequeno e fácil de rebasear.

- `state/createItvHomeController.ts`: foco, bordas sem wrap com bump, segurar OK (menu Move/Hide; nos tiles fixos só "X has a fixed place"), modo mover (troca com o app vizinho; OK grava, Back cancela), Hide, OK enfileirado durante a animação de entrada, retorno à Home focando o último usado, falha ao abrir (bump + toast "Couldn’t open X", último usado volta ao anterior).
- `model/`: funções puras. `library.ts` (ordem, escondidos, apps já vistos, último usado; `localStorage["itv.home.v1"]`), `tiles.ts` (grade de 6 colunas e vizinhança), `brands.ts` (os seis apps pelo catálogo e, como reserva, pelo nome), `ps4.ts`.
- `components/`: `ItvHome`, `Tile`, `TileArtwork`, `TileMenu`, `MoveHint`, `Wallpaper`. Logos oficiais (Wikimedia Commons, aprovados pelo usuário) em `logos/`, com o branco já embutido no SVG (sem `filter` em runtime). O Vite os embute no bundle como data URI.
- `sounds/createItvSounds.ts`: porte 1:1 do `sounds.js` do protótipo (Soft move, Wood bump, Pebble select/back/grab), em Web Audio, com um `AudioContext` criado no primeiro toque de tecla.
- `platform/createRunningApps.ts`: palpite do último usado para apps abertos fora da Home (ver checklist).
- `config.ts`: `wallpaper: "dusk"` (trocar para `"ocean"` no Mac e rebuildar) e `ps4FixedPort` (ver checklist).

Fidelidade visual: geometria do protótipo (grade em x=105/y=540, tiles 250×150, gaps 42/86, placa 1770×210), foco Lift a ~113% em 200 ms com sombra e brilho, entrada escalonada de ~0,4 s, sem labels (o texto só aparece dentro da arte: "PS4", "Apps" e o nome curto de um app instalado depois que não tenha ícone). Toda a UI está em inglês, em `copy.ts`, independente do idioma da TV.

### Edições pequenas fora do módulo

| Arquivo | Mudança | Por quê |
| --- | --- | --- |
| `src/index.ts` | Monta `mountItvHome`. O wallpaper do AeroTizen continua montado (a tela de Settings depende dele), mas nunca é aplicado. O boot não inicia clima, rede e Continue Watching. | Decisão do usuário: nada invisível rodando na TV lenta. |
| `app/startLauncherBoot.ts` | Parâmetro opcional `{ continueWatching?, status? }`, que por padrão inicia tudo como antes. | O upstream e os testes continuam iguais. |
| `contracts/apps.ts`, `services/createAppsService.ts`, `platform/tizen/createAppsPlatform.ts` | `launch` e `openStore` ganham um callback opcional de falha. Com ele, quem chama exibe a mensagem; sem ele, nada muda. Novo `openSettings`, que tenta `SETTINGS_APP_IDS` em ordem pelo mesmo caminho `prepareWatch` da loja. | Permite o bump + toast em inglês na falha e abre o Settings da Samsung. |
| `launcherConfig.ts` | `SETTINGS_APP_IDS: ["org.tizen.settings", "org.tizen.settings-tv-ref"]`. | São candidatos, a confirmar na TV. |
| `css/motion.css` | Tokens `--motion-duration-itv-*`, zerados no modo de performance e em reduced-motion. | Segue a regra upstream de tokens de movimento. |
| `tests/browser/launcher_updates.spec.cjs` | O spec do 0001 não tem mais `#gear`: espera `[data-itv-home]` e abre o Settings pela bridge. | Continua cobrindo o 0001. |
| `tests/settings_build.test.cjs` | O teste de auditoria de ícones passou a exigir `cable` em vez de `hdmi-port`. | `hdmi-port` só era usado pela Home antiga. |
| `tests/browser/itv_home.spec.cjs` (novo) | 6 cenários: layout, bordas, menu e Hide, retorno ao último usado, falha ao abrir, PS4. | — |

Ficaram intactos: `cli/`, `launcher/src/service/` (o Watcher), as identidades `DclHome001.Home`/`DclHome001.Watcher` e a integração Native Home. Isso foi verificado no clone de aplicação.

### Decisões do usuário tomadas nesta thread (além da spec)

1. O painel de configurações do próprio AeroTizen (engrenagem) ficou **inacessível**. O código continua no bundle. Para depois: [guivalenca/iTV#3](https://github.com/guivalenca/iTV/issues/3).
2. Apps que já estão instalados na **primeira execução**, fora os seis, são tratados como pré-instalados e ficam **escondidos**. Só os apps instalados depois entram na linha 2.
3. Clima, rede e Continue Watching **não são iniciados**, e o wallpaper animado do AeroTizen não é renderizado.
4. Último usado para apps abertos pelos **botões do controle**: fica um **palpite**, sem mexer no Watcher, e é item de aceitação na TV (abaixo).

### Escolhas técnicas de desempenho

Só transform e opacity são animados.

- Não há `backdrop-filter`. A placa e os tiles de apps novos são branco translúcido liso sobre o gradiente estático, sem diferença visível. O menu é opaco (`#1c1c22`), porque um menu translúcido sem blur deixava o tile de baixo aparecer como fantasma.
- O grain é um tile de ruído de 256 px gerado uma vez num canvas, com semente fixa e blend normal (sem `mix-blend-mode`), em `MAX_ALPHA 0.03`.
- Os fundos em gradiente dos tiles e o brilho do foco são imagens SVG. Pela regra do `docs/styles.md`, um gradiente CSS numa camada animada é redesenhado pela CPU da TV.
- A face do tile é desenhada no tamanho focado (284×170) e reduzida a 0,88 em repouso, então o logo focado é rasterizado nítido. A sombra profunda é uma camada à parte, que aparece por opacidade. Os tiles em repouso não têm sombra com blur.
- Com mais de duas linhas, a grade rola. Só duas linhas ficam visíveis, e a placa some junto com a linha 1.

## Como integrar

1. Copie `0002-itv-home-ui.patch` para `patches/`. A ordem é a lexical, e ele aplica depois do 0001.
2. Rode `python3.12 scripts/build.py`. Ele clona, aplica 0001 e 0002 com `git apply --check` e depois `git apply`, builda e roda `format:check`, `lint`, `test`, `test:components`, `test:service` e `typecheck`.
   - Opcional: `--browser-tests` roda o `launcher_updates.spec.cjs` adaptado.
3. Atualize `docs/build.md`: a seção do patch, os números de testes (node 567, components 195, service 13) e o hash do `.wgt`.
4. Instale o `.wgt` na TV pelo procedimento já usado na prova. Native Home e identidades não mudaram.

Verificado aqui: o patch aplica sem avisos sobre um clone limpo de `8ec95131` + 0001.

## Verificação feita no Mac (sem TV)

| Checagem | Resultado |
| --- | --- |
| `format:check`, `lint`, `typecheck`, `build` | OK (ES2018 verificado pelo build) |
| `npm test` | 567/567 |
| `test:components` | 195/195, incluindo 36 novos (módulo iTV e descoberta do Settings) |
| `test:service` | 13/13 |
| `itv_home.spec.cjs` + `launcher_updates.spec.cjs` | 9/9 com `--workers=1` |
| Suíte de navegador completa | Ver `test-output/browser-full-suite.log` e a seção "Pendências". |

Sobre o Playwright em paralelo: o `python3 -m http.server` do `playwright.config.cjs` upstream reseta conexões quando dois workers carregam páginas ao mesmo tempo (`ERR_CONNECTION_RESET` em CSS/JS, tela branca). O `docs/build.md` já registrava instabilidade parecida no upstream. Com `--workers=1` ou `--retries=1`, os specs da Home passam.

Revisões da Sol (Codex `gpt-6.1-sol`): review do plano, review visual intermediária e review final. Todos os achados foram corrigidos, exceto o que o usuário decidiu manter (o palpite do último usado). A review final terminou sem defeito visual relevante. O único bug lógico que ela apontou (um app descoberto durante o modo mover seria perdido) foi corrigido e ganhou teste de regressão.

## Checklist do que só a TV responde

**Itens novos da rodada 2:**

- **Settings:** confirmar que abre. Se não, use `apps --raw` (ver Rodada 2, item 1).
- **Transição de abrir:** confirmar que não fica preto além do carregamento do app, que a falha devolve a Home e que o PS4 (viewer nativo) também cobre/volta bem.
- **Volta com Home:** confirmar que o "zoom e zoom out" sumiu e que a Home reaparece a partir do preto.
- **Sons:**
  - avaliar o novo conjunto de cliques;
  - medir o atraso (seção acima);
  - conferir que o ruído de manutenção (−80 dBFS) é inaudível também com o volume alto, inclusive numa soundbar, e que não interfere no áudio do HDMI/PS4;
  - na TV, testar a saída em "TV Speaker" (Bluetooth soma 100–300 ms), "Digital Output Audio Delay" em 0 se houver soundbar, e comparar com "Sound Feedback" da Samsung;
  - **não** seguir sugestões de atualizar firmware.
- O beep nativo `tizen.tvaudiocontrol.playSound` foi descartado por ora: exige o privilégio `tv.audio`, que não está no `config.xml` (que não deve ser alterado).

**Itens da primeira entrega:**


Para cada item: o caminho preparado e o fallback seguro.

1. **Detecção do PS4.** O tile aparece com fonte HDMI `connected === true` e nome CEC `PS4`, `PS4 Pro`, `PlayStation 4` ou `PlayStation` (PS5 não casa).
   - Verificar o nome que a TV reporta e o que acontece com o PS4 em repouso (o tile pode sumir).
   - Se o nome não vier, defina `ps4FixedPort` em `launcher/src/itv/config.ts` com a porta HDMI e rebuilde. A porta só identifica o console; continua exigindo conexão.
2. **Último usado pelos botões do controle (item de aceitação).**
   - Aberto pela Home: registro exato.
   - Fora da Home: ao voltar, compara `tizen.application.getAppsContext()` com a foto da última volta. Se exatamente um app da grade começou a rodar (fora o que a própria Home abriu), ele vira o último usado.
   - Falha se o app já estava na memória ou se saiu com Back. Na dúvida, mantém o último confirmado.
   - Testar: abrir Netflix pelo botão, apertar Home e ver se o foco está nele. Repetir com o app já aberto antes.
   - Se não bastar, abrir uma issue para o Watcher registrar o app em primeiro plano em modo Native. É uma mudança no serviço e precisa de review própria.
3. **Home na própria Home.** Espera-se um `appcontrol` com operação `main` (Native Home relança o launcher), que move o foco para o último usado. Confirmar que esse evento chega com o launcher visível.
4. **Settings da Samsung.** Os candidatos são `org.tizen.settings` e `org.tizen.settings-tv-ref`.
   - Na falha: bump + "Couldn’t open Settings", e a Home fica.
   - Achar o ID real na lista de apps instalados (nome "Settings") e ajustar `SETTINGS_APP_IDS`.
5. **Tile Apps.** Usa `apps.openStore()` do upstream (`com.samsung.tv.store`, depois `org.volt.apps`). Confirmar que abre a loja.
6. **Lista de apps e pré-instalados.**
   - Na primeira execução, conferir que aparecem os seis em ordem e mais nada.
   - Se algum app que o usuário instalou sumir, ele está em `known` de `localStorage["itv.home.v1"]`. Ainda não existe "mostrar escondidos" (é trabalho futuro), então seria preciso ajustar o storage.
   - Conferir também que instalar um app pela loja o coloca na linha 2.
7. **Latência e volume dos sons.** O primeiro som cria o `AudioContext`. Medir o atraso entre tecla e som, conferir com música tocando em segundo plano (deve ficar mais baixo que a música) e se o primeiro toque após ligar a TV toca. Se o atraso for perceptível, reportar antes de enviar (regra da spec).
8. **Desempenho.**
   - Fluidez do foco (200 ms), do bump, do wiggle e da entrada de 0,4 s.
   - Custo do grain: comparar com `MAX_ALPHA 0` em `createGrainTile.ts` se houver lentidão.
   - Banding do gradiente no painel de 50": se aparecer, subir o grain um pouco, para 0,04.
   - Se precisar, o modo de performance do AeroTizen zera todas as animações da Home pelos tokens, mas o painel está inacessível. Hoje isso só se aplica via storage.
9. **Legibilidade no sofá (50").** Logos, "PS4"/"Apps", nomes de apps sem ícone, toast e dica de mover.
10. **Ícones de apps instalados depois.** Usa o `iconPath` que a TV reporta. Se não carregar, mostra o nome curto do app. Conferir com um app real da loja.
11. **Back e retorno.** Back dentro dos apps funciona normalmente. Back na Home não faz nada e nunca leva a tela preta ou à UI da Samsung. Conferir também que o PS4 (HDMI via viewer nativo) volta para a Home com foco no PS4.
12. **Power-on.** Ao ligar, foco no último usado; se for o PS4 desligado, foco no primeiro tile. Um OK durante a entrada abre o app no fim dela.

## Pendências e decisões em aberto

- **Suíte de navegador do upstream.** Specs que exercitam a Home antiga (cabeçalho, `#gear`, abas, dock de entradas, Continue Watching na Home, layouts de cards) falham porque essa Home não é mais montada. Elas não fazem parte das checagens obrigatórias nem do `build.py --browser-tests`. A execução completa foi interrompida após ~135 dos 374 testes (cada falha esperava o timeout; levaria mais de 1 h): até ali, 254 falhas contando retentativas, em 50 arquivos — lista por arquivo em `test-output/browser-full-suite-failures-by-file.txt`, log em `test-output/browser-full-suite.log`. São basicamente specs que usam a Home antiga ou o `#gear`, ou esperam clima/rede/Continue Watching iniciados; parte pode ser o reset do `http.server` com 2 workers. Decidir depois se esses specs saem do fork ou se a Home antiga é removida, o que daria um patch bem maior.
- **Linha 3 em diante.** Fica escondida até o foco descer (sem "espiar" a linha seguinte), porque a spec e o protótipo não tratavam mais de duas linhas. Revisar quando o usuário tiver mais apps.
- **Mostrar apps escondidos e acessar o painel do AeroTizen.** Fora do escopo (spec e issue #3).
- **Toasts** usam o componente de toast do launcher (tema classic). A dica de mover é própria da Home e copia o estilo do toast.
- **Long press:** usa `LONG_PRESS_MS = 600` do upstream (o protótipo usava 650).
- Os commits do clone de trabalho (`.cache/home-ui-dev/aerotizen`, branch `itv/home-ui`) não têm valor próprio: o entregável é o patch.

## Screenshots

`00` protótipo · `01` entrada pausada em 140 ms · `02` primeira execução · `10-focus-00..10` foco em cada tile (seis apps, dois apps novos — com ícone e sem ícone —, PS4, Settings, Apps) · `20`/`21` bump nas bordas (pausado) · `30`/`31` menu de segurar OK · `32` modo mover com dica · `33` após trocar · `34` após cancelar com Back · `40` toast de tile fixo · `50` após Hide · `60` PS4 desconectado · `70` falha ao abrir · `80`/`81` três linhas (topo e rolado).

Em todos: inventário injetado pelo harness, com os seis apps pelos IDs reais do catálogo, um pré-instalado escondido e PS4 na HDMI 1.
