# 📻 Sistema de Alertas Geográficos via RDS

> Arquitetura experimental para disseminação de alertas hierarquicamente endereçados utilizando **RDS (Radio Data System)** sobre radiodifusão FM, com um orquestrador em Python, um transmissor **ESP32 + Si4713** e nós receptores **ESP8266 + Si4703** acionando sirenes locais.

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![Arduino](https://img.shields.io/badge/Arduino-C%2B%2B-00979D?logo=arduino)](https://www.arduino.cc/)
[![ESP32](https://img.shields.io/badge/ESP32-Transmissor-E7352C?logo=espressif)](https://www.espressif.com/)
[![ESP8266](https://img.shields.io/badge/ESP8266-Receptor-E7352C?logo=espressif)](https://www.espressif.com/)

Este repositório reúne o software e os firmwares de uma prova de conceito para **alertas públicos distribuídos por RDS**, utilizando uma hierarquia lógica de endereçamento para direcionar mensagens a diferentes regiões.

O sistema opera em três componentes principais: uma central gráfica em Python, um gateway de transmissão conectado ao computador por USB/Serial e um receptor de borda que monitora mensagens RDS e aciona uma sirene quando o identificador recebido corresponde à sua configuração local.

A implementação fornecida utiliza a frequência **106,1 MHz** e transporta o comando no campo de texto RDS, com um protocolo compacto de **6 caracteres**: cinco dígitos de identificação geográfica e um dígito representando o estado do alarme.

> **Aviso:** este projeto é experimental e acadêmico. Não deve ser utilizado como sistema real de alerta público ou emergência sem os requisitos de confiabilidade, segurança, redundância, validação e conformidade regulatória aplicáveis. Transmissões em FM devem ser realizadas somente em condições permitidas pela regulamentação local.

---

## ⚙️ Arquitetura do Sistema

O ecossistema é dividido em três camadas:

1. **Orquestrador / Command Center (`main.py`)**  
   Interface gráfica desenvolvida com `CustomTkinter`. Gerencia portas seriais, cadastro lógico de regiões, seleção do alvo, provisionamento dos IDs dos receptores e envio dos comandos de alarme.

2. **Nó Transmissor / Gateway (`TXsi4713_esp32.ino`)**  
   Um ESP32 recebe o payload pela USB/Serial a **115200 bps**, controla o módulo **Si4713** por I²C e injeta a mensagem no RDS da transmissão FM em **106,1 MHz**.

3. **Nó Receptor / Sirene (`RXSi4703_esp8266.ino`)**  
   Um ESP8266 com **Si4703** monitora o RDS, compara o ID recebido com seus identificadores geográficos armazenados e executa o padrão sonoro correspondente por meio de um buzzer passivo.

### Fluxo ponta a ponta

```text
┌──────────────────────────────┐
│      Command Center          │
│          Python              │
│  cadastro + alvo + comando   │
└──────────────┬───────────────┘
               │ USB / Serial 115200 bps
               ▼
┌──────────────────────────────┐
│       ESP32 + Si4713         │
│      Gateway Transmissor     │
│        FM 106.1 MHz          │
└──────────────┬───────────────┘
               │ RDS / RadioText
               ▼
┌──────────────────────────────┐
│      ESP8266 + Si4703        │
│       Receptor de Borda      │
│  filtro por ID + motor de    │
│        estado da sirene      │
└──────────────┬───────────────┘
               ▼
        🔊 Buzzer / Sirene
```

---

## 🧭 Endereçamento Geográfico Hierárquico

Cada receptor mantém quatro possibilidades de identificação:

| Nível | ID | Persistência |
| :--- | :---: | :--- |
| Nacional | `00000` | Fixo no firmware |
| Estadual | `XXXXX` | Configurável e salvo em EEPROM |
| Municipal | `XXXXX` | Configurável e salvo em EEPROM |
| Bairro / Zona | `XXXXX` | Configurável e salvo em EEPROM |

O ID nacional `00000` é reservado para mensagens aceitas por **todos os receptores**.

No firmware fornecido, quando ainda não existe provisionamento salvo na EEPROM, o receptor inicia com os seguintes valores padrão:

```text
ID_NACIONAL  = 00000
ID_ESTADUAL  = 00010
ID_MUNICIPAL = 00011
ID_BAIRRO    = 00012
```

Ao receber uma mensagem, o nó verifica se os cinco primeiros caracteres correspondem a pelo menos um destes quatro IDs. Somente mensagens destinadas ao nó são encaminhadas para o motor de estado da sirene.

---

## 📡 Formato do Payload RDS

O comando lógico possui **6 caracteres**:

```text
IIIIIA
```

Onde:

- `IIIII` = identificador geográfico de 5 dígitos;
- `A` = ação de alarme representada por um dígito entre `0` e `3`.

### Exemplos

```text
000003
```

Dispara **evacuação crítica em nível nacional**.

```text
000122
```

Dispara **aviso preventivo** para o receptor cujo ID configurado seja `00012`.

```text
000120
```

Silencia o alarme do receptor identificado por `00012`.

### Estados implementados

| Ação | Estado | Comportamento no receptor | RDS Program Service no TX |
| :---: | :--- | :--- | :--- |
| `0` | Silenciar | Desliga o buzzer imediatamente | `ALERTA` |
| `1` | All Clear / Seguro | Tom de **1500 Hz por 2 s** e retorno automático ao estado `0` | `SEGURO` |
| `2` | Aviso Preventivo | **800 Hz**, alternando 1 s ligado / 1 s desligado | `ATENCAO!` |
| `3` | Evacuação Crítica | Alternância entre **1200 Hz e 1800 Hz a cada 300 ms** | `EVACUAR!` |

O transmissor completa o texto recebido com espaços até **64 caracteres** antes de enviá-lo para o buffer RDS. Caso a entrada seja maior que 64 caracteres, ela é truncada.

---

## 💾 Provisionamento dos Receptores

Os IDs estadual, municipal e de bairro podem ser alterados sem recompilar o firmware.

Para isso, conecte o **ESP8266 receptor** diretamente ao computador e utilize o painel **Provisionamento (Sirene USB)** do software Python.

O Command Center envia pela serial o comando:

```text
GRAVAR_IDS:EEEEE,MMMMM,BBBBB
```

Exemplo:

```text
GRAVAR_IDS:00010,00011,00012
```

O receptor grava os três identificadores na EEPROM e responde:

```text
EEPROM_OK
```

O byte inicial da EEPROM é utilizado como uma flag de validade. Após uma gravação bem-sucedida, os IDs permanecem disponíveis mesmo após reinicialização ou perda de energia.

> Utilize sempre IDs numéricos entre `00000` e `99999`, mantendo exatamente cinco dígitos por nível.

---

## 🖥️ Funcionalidades do Command Center

O arquivo `main.py` implementa uma interface gráfica com três áreas funcionais.

### 1. Georreferenciamento lógico

Permite cadastrar regiões em uma árvore de navegação contendo:

- Estado;
- Município;
- Bairro / zona;
- ID numérico de 5 dígitos.

Também existe busca por nome da região ou ID.

O cadastro lógico pode representar:

- **Alerta estadual:** Estado preenchido, município vazio;
- **Alerta municipal:** Estado e município preenchidos, bairro vazio;
- **Alerta de bairro/zona:** Estado, município e bairro preenchidos.

### 2. Provisionamento

Quando o software identifica um **receptor**, os campos de provisionamento são habilitados e os botões de disparo ficam bloqueados.

O operador pode gravar os três IDs geográficos diretamente na memória do ESP8266 pela conexão USB.

### 3. Disparo de alarmes

Quando o software identifica um **transmissor**, o provisionamento é bloqueado e os comandos de alarme são habilitados:

- 🟢 `ALL CLEAR (SEGURO)`;
- 🟡 `AVISO PREVENTIVO`;
- 🔴 `EVACUAÇÃO CRÍTICA`;
- ⏹ `SILENCIAR SIRENES`.

O payload enviado ao ESP32 é criado automaticamente a partir do nó selecionado:

```python
payload = f"{id_alvo}{comando}\n"
```

---

## 🔌 Identificação dos Dispositivos pela Serial

O software diferencia automaticamente o tipo de hardware conectado.

### Receptor

O Python envia:

```text
PING_ID
```

O receptor responde:

```text
SYS_ID:RECEPTOR
```

### Transmissor

Durante a inicialização, o firmware do ESP32 anuncia:

```text
SYS_ID:TRANSMISSOR
```

A partir dessa assinatura, a interface habilita o conjunto de controles correspondente ao dispositivo.

### Nota sobre a implementação atual do TX

O firmware fornecido do transmissor **não possui um tratamento dedicado para `PING_ID`**. Ele anuncia `SYS_ID:TRANSMISSOR` durante o `setup()` e trata qualquer outra linha recebida como conteúdo potencial para o RDS.

Portanto, a identificação do transmissor depende de o Command Center capturar a assinatura emitida na inicialização. Para uma versão futura mais robusta, recomenda-se implementar no TX a mesma resposta explícita utilizada pelo receptor:

```cpp
if (payloadPython == "PING_ID") {
    Serial.println("SYS_ID:TRANSMISSOR");
    return;
}
```

---

## 🛠️ Materiais Necessários

### Transmissor

- 1x ESP32;
- 1x módulo transmissor FM **Si4713**;
- antena/conexão RF apropriada ao módulo e ao ambiente experimental;
- jumpers;
- protoboard ou montagem equivalente;
- cabo USB para comunicação com o computador.

### Receptor

- 1x ESP8266 / NodeMCU;
- 1x módulo receptor FM **Si4703**;
- 1x buzzer passivo;
- conexão/antena adequada ao módulo receptor;
- jumpers;
- protoboard ou montagem equivalente;
- cabo USB para provisionamento.

---

## 🔌 Esquema de Ligação

### Transmissor — ESP32 + Si4713

| ESP32 | Si4713 | Função |
| :---: | :---: | :--- |
| `3V3` | Alimentação compatível do módulo | Alimentação |
| `GND` | `GND` | Referência elétrica |
| `GPIO 21` | `SDA` | Dados I²C |
| `GPIO 22` | `SCL` | Clock I²C |
| `GPIO 27` | `RST` | Reset do Si4713 |

No firmware:

```cpp
#define RESET_PIN 27
Wire.begin(21, 22);
```

### Receptor — ESP8266 + Si4703

| ESP8266 / NodeMCU | Si4703 / Buzzer | Função |
| :---: | :---: | :--- |
| `3V3` | Alimentação compatível do Si4703 | Alimentação |
| `GND` | `GND` | Referência elétrica |
| `D2 / GPIO 4` | `SDA` | Dados I²C |
| `D1 / GPIO 5` | `SCL` | Clock I²C |
| `D5 / GPIO 14` | `RST` | Reset do Si4703 |
| `D6 / GPIO 12` | Buzzer passivo | Saída da sirene |

No firmware:

```cpp
#define PINO_RESET 14
const int PINO_SIRENE = 12;
Wire.begin(4, 5);
```

> Confirme sempre a tensão de alimentação exigida pela placa breakout específica utilizada. Os GPIOs dos ESP32/ESP8266 trabalham em lógica de 3,3 V.

---

## 📦 Dependências

### Python

O Command Center utiliza:

- `customtkinter`;
- `pyserial`;
- `tkinter` / `ttk`;
- `threading`, `datetime` e `time` da biblioteca padrão.

Instalação das dependências externas:

```bash
pip install customtkinter pyserial
```

> Em algumas distribuições Linux, o `tkinter` precisa ser instalado pelo gerenciador de pacotes do sistema operacional.

### Arduino / Firmware

Para o transmissor:

- `Wire`;
- `Adafruit Si4713 Library`.

Para o receptor:

- `Wire`;
- `EEPROM`;
- `PU2CLR SI470X`.

Também é necessário instalar na Arduino IDE os pacotes de placa correspondentes ao **ESP32** e ao **ESP8266**.

---

## 🚀 Instalação

### 1. Firmwares

1. Instale a Arduino IDE.
2. Instale os pacotes de placas ESP32 e ESP8266.
3. Instale as bibliotecas `Adafruit Si4713 Library` e `PU2CLR SI470X`.
4. Abra `TXsi4713_esp32.ino`, selecione a placa ESP32 correta, compile e grave o transmissor.
5. Abra `RXSi4703_esp8266.ino`, selecione a placa ESP8266 correta, compile e grave o receptor.
6. Monte os circuitos conforme a pinagem descrita neste README.

### 2. Command Center

Recomenda-se utilizar um ambiente virtual Python:

```bash
python -m venv .venv
```

Ative o ambiente virtual.

**Windows:**

```bash
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install customtkinter pyserial
```

Execute a aplicação:

```bash
python main.py
```

---

## ▶️ Tutorial de Operação

### Etapa A — Provisionar uma sirene

1. Grave `RXSi4703_esp8266.ino` no ESP8266.
2. Conecte o receptor ao computador via USB.
3. Execute `main.py`.
4. Selecione a porta serial do ESP8266 e clique em **CONECTAR DISPOSITIVO**.
5. Após a resposta `SYS_ID:RECEPTOR`, o painel de provisionamento será habilitado.
6. Informe os IDs estadual, municipal e de bairro/zona.
7. Clique em **Gravar IDs na Placa**.
8. Aguarde a confirmação `EEPROM_OK` no log.
9. Desconecte o receptor do computador e mantenha-o energizado no local de teste.

### Etapa B — Cadastrar os alvos no software

1. No painel de georreferenciamento, informe Estado, Município, Bairro/Zona e o ID correspondente.
2. Clique em **Adicionar Região à Árvore**.
3. Repita o processo para os demais alvos que deseja controlar.
4. Utilize o campo de busca para localizar uma região ou ID.

### Etapa C — Transmitir um alerta

1. Grave `TXsi4713_esp32.ino` no ESP32.
2. Conecte o transmissor ao computador via USB.
3. No Command Center, selecione a porta serial do ESP32.
4. Após a identificação como transmissor, selecione um nó `[XXXXX]` na árvore.
5. Clique no nível de alerta desejado.
6. O Python envia o payload pela USB/Serial.
7. O ESP32 atualiza o RadioText RDS e o transmite em 106,1 MHz.
8. Cada receptor verifica se o ID recebido corresponde a `NACIONAL`, `ESTADUAL`, `MUNICIPAL` ou `BAIRRO` configurado localmente.
9. Os receptores compatíveis executam o padrão sonoro correspondente.

---

## 🔬 Detalhes de Engenharia

### Desativação de DTR/RTS

Ao abrir a porta serial, o Command Center desativa explicitamente DTR e RTS:

```python
self.porta_serial.setDTR(False)
self.porta_serial.setRTS(False)
```

Essa estratégia busca reduzir resets indesejados causados pela abertura da conexão serial em placas da família ESP.

### Memória não volátil

O receptor reserva 64 bytes de EEPROM emulada. A organização utilizada é:

| Endereço | Conteúdo |
| :---: | :--- |
| `0` | Flag `'G'`, indicando configuração válida |
| `1–5` | ID estadual |
| `6–10` | ID municipal |
| `11–15` | ID de bairro/zona |

### RDS e deduplicação

O receptor lê o texto RDS 2A com `getRdsText2A()` e mantém a última mensagem processada em memória. Um payload só é reavaliado quando o texto recebido é diferente de `ultimaMensagem`.

Isso evita processamento repetitivo do mesmo RadioText, mas significa que **mensagens idênticas consecutivas são deduplicadas**. Em particular, após o comando `1` (All Clear) terminar automaticamente depois de 2 segundos, reenviar exatamente o mesmo payload sem uma mensagem intermediária pode não gerar um novo acionamento.

### Controle não bloqueante da sirene

Os padrões sonoros são controlados com `millis()` e comparações temporais. Não são utilizados `delay()` dentro da função de execução da sirene, permitindo que o loop continue verificando a serial e novos dados RDS durante o acionamento.

### RDS Program Service dinâmico

Além do RadioText, o transmissor altera o nome curto da estação conforme a ação:

```text
0 -> ALERTA
1 -> SEGURO
2 -> ATENCAO!
3 -> EVACUAR!
```

Isso permite que um receptor veicular compatível também apresente uma indicação textual curta associada ao estado transmitido.

---

## ⚠️ Limitações da Implementação Atual

- O cadastro da árvore geográfica em `main.py` existe apenas em memória e **não é persistido em arquivo ou banco de dados**; ao encerrar a aplicação, os nós cadastrados durante a execução são perdidos.
- A persistência em EEPROM vale somente para os três IDs configurados no receptor.
- O transmissor não possui resposta dedicada ao comando `PING_ID`; sua identificação é anunciada durante a inicialização.
- O protocolo não possui autenticação, assinatura digital, criptografia ou mecanismo de integridade de mensagem.
- O receptor aceita uma mensagem pela correspondência textual do ID; o modelo atual não implementa confirmação de entrega ou retorno pelo enlace RDS.
- O TX considera o sexto caractere como ação quando recebe uma linha com pelo menos 6 caracteres. A interface Python restringe os comandos normais a `0`, `1`, `2` e `3`, mas o firmware do TX não faz validação completa do payload.
- RadioText idêntico é deduplicado no receptor.
- A frequência está fixada em `10610` no código das bibliotecas, correspondente a **106,1 MHz**; alterá-la exige manter TX e RX configurados na mesma frequência.

---

## 📁 Estrutura Recomendada do Repositório

Uma organização simples para publicação no GitHub é:

```text
.
├── main.py
├── firmware/
│   ├── TXsi4713_esp32/
│   │   └── TXsi4713_esp32.ino
│   └── RXSi4703_esp8266/
│       └── RXSi4703_esp8266.ino
├── README.md
└── LICENSE
```

Se preferir manter os três códigos na raiz, ajuste apenas os caminhos mostrados no tutorial.

---

## 🧪 Possíveis Extensões

A arquitetura atual permite evoluções como:

- persistência do mapa lógico em JSON, SQLite ou outro banco de dados;
- validação rígida do formato `IIIIIA` nos dois firmwares;
- resposta explícita a `PING_ID` no transmissor;
- registro de eventos e exportação de logs;
- mecanismos de autenticação e integridade dos comandos;
- múltiplos transmissores e redundância de cobertura;
- métricas experimentais de latência, taxa de recepção, alcance e perda de mensagens;
- testes com diferentes níveis hierárquicos e múltiplos receptores simultâneos.

---

## 📚 Citação

Caso este repositório acompanhe um artigo científico, substitua os campos abaixo pelos metadados definitivos da publicação antes de disponibilizar a versão final:

```bibtex
@inproceedings{TODO2026RDSAlert,
  title     = {TÍTULO DO ARTIGO},
  author    = {AUTORES},
  booktitle = {Anais do Simpósio Brasileiro de Sistemas Multimídia e Web (WebMedia)},
  year      = {2026},
  publisher = {SBC}
}
```

---

## 📄 Licença

Defina a licença do projeto antes da publicação e adicione o arquivo `LICENSE` correspondente ao repositório.

Se este trabalho utilizar a mesma política de licenciamento do projeto de referência, atualize esta seção com a licença escolhida e o respectivo badge no topo do documento.
