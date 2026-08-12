#include <Wire.h>
#include <Adafruit_Si4713.h>

#define RESET_PIN 27
#define FM_FREQ 10610 

Adafruit_Si4713 radio = Adafruit_Si4713(RESET_PIN);

void setup() {
  Serial.begin(115200); 
  
  // 1. HARDWARE RESET MANUAL
  pinMode(RESET_PIN, OUTPUT);
  digitalWrite(RESET_PIN, LOW);
  delay(100); 
  digitalWrite(RESET_PIN, HIGH); 
  delay(50); 
  
  // 2. APRESENTAÇÃO E INICIALIZAÇÃO
  Serial.println("SYS_ID:TRANSMISSOR");
  
  Wire.begin(21, 22);

  if (! radio.begin()) {
    Serial.println("❌ Erro: Si4713 não encontrado!");
    while (1); 
  }

  radio.setTXpower(115);
  radio.tuneFM(FM_FREQ);
  
  // Nome da Estação Padrão
  radio.setRDSstation("ALERTA  ");
  
  // Mensagem inicial de espera
  radio.setRDSbuffer("Aguardando o Python...                                          ");
  radio.beginRDS();

  Serial.println("✅ Transmissor Pronto! 106.1 MHz.");
  Serial.println("🎧 Aguardando injeção de dados via Serial...");
}

void loop() {
  // Verifica se o Python mandou alguma coisa pela porta USB
  if (Serial.available() > 0) {
    
    String payloadPython = Serial.readStringUntil('\n');
    payloadPython.trim(); 

    if (payloadPython.length() > 0) {
      Serial.print("📥 Recebido do Python: [");
      Serial.print(payloadPython);
      Serial.println("]");

     
      // Verifica se o pacote tem o formato do nosso Alarme (ID de 5 digitos + Ação de 1 dígito)
      if (payloadPython.length() >= 6) {
         char acao = payloadPython.charAt(5); // Pega a ação (0, 1, 2 ou 3)
         
         // Atualiza dinamicamente o letreiro dos rádios veiculares (Máx 8 caracteres)
         if (acao == '3') {
            radio.setRDSstation("EVACUAR!"); 
         } else if (acao == '2') {
            radio.setRDSstation("ATENCAO!"); 
         } else if (acao == '1') {
            radio.setRDSstation("SEGURO  "); 
         } else if (acao == '0') {
            radio.setRDSstation("ALERTA  "); // Volta ao estado neutro
         }
      }
      // ==================================================

      while (payloadPython.length() < 64) {
        payloadPython += " ";
      }
      if (payloadPython.length() > 64) {
        payloadPython = payloadPython.substring(0, 64);
      }

      // Converte a String do Arduino para o formato C que a biblioteca exige
      radio.setRDSbuffer(payloadPython.c_str());
      
      Serial.println("🚀 Payload injetado no ar via RDS com sucesso!");
    }
  }
  
  delay(100); 
}