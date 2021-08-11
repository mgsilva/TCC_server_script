#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Script que ira receber as mensagens mqtt postadas pelo esp.
# importa o modulo para tratar o cliente mqtt
import paho.mqtt.client as mqttClient 
import numpy
from matplotlib import pyplot as plt
from scipy import fft, signal
import csv

import time
#O script roda na mesma máquina que o broker
broker = 'localhost'
# broker = "mqtt.eclipse.org"
# broker = 'matheusserver.ddns.net'

dataset = 0

msg_received = ""
flag_msg_received = False
def processMessage(messagetosave):
    global dataset
    V_ref = 5
    nbits = 4096
    adc_res = V_ref/nbits
    i = 0
    k = 0
    recv_data = []
    # Formatando o dado recebido
    # A taxa de amostragem é de aproximadamente 10Khz
    # O sinal é amostrado por 5s -> 50K amostras
    # Como o dado possui 12 bits, ele está divido em dois bytes
    while i <100000:
        msb = (messagetosave[i]<<8)
        i+=1
        lsb = messagetosave[i]
        i+=1
        value = msb | lsb
        value = value * adc_res # valor em V
        value = (30*value)/2.5
        recv_data.append(value) # Dado convertido
    j = 0
    # Os ultimos 4 bytes é o tempo que o esp demorou para aquisitar as 50K amostras
    # Vai ser utilizado para calcular os parametros da fft
    total_time = ((messagetosave[100000] << 24) | \
            (messagetosave[100001] << 16) | \
            (messagetosave[100002] << 8) | \
            messagetosave[100003])/1000000

    ###### Salvando sinal em um arquivo csv

    with open('current_signal_{}.csv'.format(str(dataset)), mode='w') as signal_file:
        out_data = csv.writer(signal_file, delimiter=',')
        out_data.writerow(recv_data)
    dataset += 1
    # Removendo a componente DC do sinal.
    # O ADC mede de 0 a 4096. a saida do ACS varia de 0 a 5V, sendo 0V -30A e 5V +30
    recv_data = recv_data - numpy.mean(recv_data)

    time_adc = total_time / 50000 #intervalo entre amostras -> aprox. 100uS
    sample_rate = 50000/total_time #Taxa de amostragem -> aprox. 10KHz
    time_step = 1/sample_rate
    print('Quantidade de dados: ' + str(100000))
    print('total time: ' + str(total_time))
    print('time step: ' +str(time_adc))
    print('sample rate: ' + str(sample_rate))
    # #### FIltrando sinal - Aqui foi um implementado um filtro digital, mas no final não foi necessario
    # nyq_rate = sample_rate / 2.0
    # width = 5/nyq_rate
    # ripple_db = 80
    # N, beta = signal.kaiserord(ripple_db, width)
    # cutoff_hz = 1000
    # taps = signal.firwin(N, cutoff_hz/nyq_rate, window=('kaiser',beta))
    # recv_data = signal.lfilter(taps, 1.0, recv_data)
    #################
    # ### Calcula transformada de fourrier, foi substituido pelo metodo magnitude_spectrum
    # fft_transform_complex = fft.fft(recv_data)
    # fourrier_transform = 2/50000 * numpy.abs(fft_transform_complex) #Tira o módulo e normaliza o valor
    # sample_frequencies = fft.fftfreq(50000, time_step)
    
    # Cria uma imagem com dois graficos
    fig, axs = plt.subplots(2, 1, constrained_layout=True)
    fig.suptitle('Sinal e FFT')
    # plota o sinal recebido
    axs[0].plot(recv_data)
    axs[0].set_xlim([0,450])
    axs[0].set_title('Sinal')
    axs[0].set_ylabel('Corrente [A]')
    axs[0].set_xlabel('Amostra [n]')
    # calcula e plota a transformada de fourrier do sinal
    axs[1].magnitude_spectrum(recv_data, sample_rate, sides='onesided',linewidth=0.5, scale='dB')
    axs[1].set_xlim([0,500])
    axs[1].set_title('FFT')
    axs[1].set_ylabel('Amplitude')
    axs[1].set_xlabel('Frequência [Hz]')
    plt.show()

#Funcao de callback para conexão
def connectionCallback(client, userdata, flags, rc):
    if rc==0:
        print("Conectou ao servidor")
        client.subscribe('/topic/tcc-iot') #Se inscreve no tópico para receber mensagens
    else:
        print ("Não conseguiu conectar!")

def messageReceivedCallback(client, userdata, msg):
    # Recebeu mensagem, vai tratar a mensagem
    # processMessage(msg.payload)
    global flag_msg_received
    global msg_received 
    msg_received = msg.payload
    flag_msg_received = True


#Funcao de callback para log da conexão
def logCallback(client, userdata, level, buf):
    print("log: "+buf)

def startMqtt():
    client = mqttClient.Client(client_id="TCC_Matheus_PC") #Cria uma instancia do cliente
    client.on_connect = connectionCallback #Linka função de callback ao evento de conexão
    client.on_log = logCallback #linka funçao de callback ao evento de log
    client.on_message = messageReceivedCallback #Linka função de callback ao evento de receber mensagem
    client.connect(broker) #Conecta ao broker
    client.loop_start() #Inicia loop do client.
    global flag_msg_received
    global msg_received    
    while True:
        if(flag_msg_received):
            flag_msg_received = False
            processMessage(msg_received)
        time.sleep(1)

    client.loop_stop()
    client.disconnect()

if __name__=='__main__':
    try:
        startMqtt()
    except KeyboardInterrupt:
        print("Fechando programa...")
    # except Exception as err:
    #     print("Exception: {}".format(str(err)))
    finally:
        pass