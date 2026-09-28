# Artigo-base: SPAPI-Tester

**Referência:** Shuai Wang, Yinan Yu, Robert Feldt (Chalmers University of Technology) e Dhasarathy Parthasarathy (Volvo Group). *Automating a Complete Software Test Process Using LLMs: An Automotive Case Study.* **Confirmar ano e veículo de publicação antes de citar.**

**Fonte deste resumo:** apresentação da disciplina *Verificação, Validação e Testes de Software* (Mestrado Profissional em Computação Aplicada, UnB), por Douglas dos Santos Lopes e Pedro Britto Júnior. Números e frases abaixo vêm dos slides; na monografia, citar sempre o texto do artigo.

## Problema

Testar a API de serviços do caminhão (SPAPI) exige confirmar que uma chamada HTTP mudou o estado do veículo simulado exatamente como a interface especifica. Para escrever cada teste, o engenheiro faz um "de-para" entre três fontes em silos, com terminologias e ferramentas diferentes:

1. **Swagger** da API (objetos e valores, ex.: `acMode: STANDARD | ECONOMY`);
2. **Tabelas de sinais CAN** (ex.: `APIACModeRqst`);
3. **Documentação do Veículo Virtual** (mock; ex.: `apiacmode_rqst`).

Processo manual em oito etapas: (1) entender a especificação da API, (2) buscar informações do sistema, (3) buscar especificações de sinal CAN, (4) buscar a documentação de mocking, (5) organizar informações entre silos, (6) escrever o caso de teste, (7) executar, (8) avaliar. As etapas 1–6 dependem de conhecimento implícito acumulado por anos; só 7–8 eram automatizadas.

## Por que um script determinístico não basta — categorias de atrito

| Categoria | Exemplo no artigo |
| --- | --- |
| Erros ortográficos | `DriverTimeSetting` × `DriverTimeSeting` |
| Abreviações | `standard` × `STD` |
| Formatos de escrita | `standard_mode` × `STANDARDMODE` |
| Equivalências lógicas | `OFF` × `NOT_ON` |
| Equivalências semânticas | `AutoStart` × `AutoLaunch` |
| Unidades inconsistentes | W × kW; km/h × m/s |
| Pseudocódigo informal | `AlarmClockStat: Active OR Snoozed` |
| Dependências complexas | `PUT /time` ativa 3 ECUs diferentes |

Um script precisaria de um dicionário de sinônimos de manutenção inviável; o gargalo era a resolução cognitiva de ambiguidades.

## Arquitetura

- **Preservação estrutural:** mantém as oito etapas originais; o LLM automatiza só as de tradução (extração, preparação, limpeza e mapeamento de parâmetros). Não usa prompts abertos.
- **DSPy:** assinaturas com tipos de entrada e esquema exato de saída; programação em vez de engenharia de prompt; **autocorreção** — captura a exceção de parsing, injeta a mensagem de erro no histórico e refaz a chamada.
- **`dspy.ChainOfThought`:** extrai o contexto de cada sinal isoladamente e justifica a relação API ↔ CAN antes de fechar o dicionário; o raciocínio intermediário fica registrado (rastreabilidade, mitigação de alucinação).
- **Saída do LLM:** dicionário JSON unificado (propriedade da API → sinal CAN → estado do VV, com os mapeamentos de valores).
- **Estágio determinístico:** o dicionário é injetado em templates **Jinja** que geram o script **PyTest**. O LLM não tem contato com o código de teste.

## Resultados (como apresentados nos slides — conferir no artigo)

| Métrica | Engenheiro sênior (manual) | SPAPI-Tester |
| --- | --- | --- |
| Tempo por API | 2 h a 3 dias | ~11 s |
| Cobertura de teste | ~82% | ~85% |
| Taxa de sucesso | 87,5% | 98,0% (GPT-4o) |

- Outros modelos: GPT-3.5 (93%), LLaMA3.1 (95%); **LLaMA3 70B (pesos abertos, hospedável localmente) no nível do modelo proprietário**.
- Precisão média por categoria: ortográficos/semânticos 0,95; equivalências lógicas 0,98; unidades 0,96; pseudocódigo 0,94.
- Validação real: **193 APIs** inéditas de um fabricante de caminhões; **22 bugs** genuínos encontrados antes da produção.
- Portar o método para outro fabricante: estimativa de cerca de um dia útil.

## Lições que o TCC adota

1. **LLM embutido, não substituto:** módulos estruturados → camada semântica LLM → módulos estruturados. LLMs não devem contornar fluxos estruturados; devem executar, dentro deles, as tarefas que exigem julgamento.
2. **Saída tipada e validada**, com autocorreção quando o parsing falha.
3. **O LLM nunca escreve o artefato executado**: entrega dados; templates determinísticos geram o código.
4. **Focar no processo, não no modelo:** o mesmo pipeline funciona com LLMs diferentes sem adaptação.
5. **Avaliar como o artigo:** humano × ferramenta, por categoria de atrito, por modelo e em casos reais.

Mapeamento para o domínio deste repo: [`proposta.md`](proposta.md) (seção "Artigo-base") e ADR 0011.

## Trabalhos relacionados citados pelo artigo

Kim et al., *Leveraging Large Language Models to Improve REST API Testing*; Golmohammadi, Zhang e Arcuri, *Testing RESTful APIs: A Survey*; Zhang, Marculescu e Arcuri, *Resource-based Test Case Generation for RESTful Web Services*; Deepika Sri et al., *Automating REST API Postman Test Cases Using LLM*. Segundo os slides, nenhum deles garantia a validade e a robustez dos casos de teste gerados.
