import time
import random
import yaml
from paho.mqtt import client as mqtt_client

# Load configuration from config.yaml
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

broker = config['MQTT_HOST']
inverter_ip = config['INVERTER_IP']
inverter_sn = config['INVERTER_SN']
port = config['MQTT_PORT']
topic = config['MQTT_TOPIC']
FIRST_RECONNECT_DELAY = config['FIRST_RECONNECT_DELAY']
RECONNECT_RATE = config['RECONNECT_RATE']
MAX_RECONNECT_COUNT = config['MAX_RECONNECT_COUNT']
MAX_RECONNECT_DELAY = config['MAX_RECONNECT_DELAY']
POLLING_INTERVAL = config['POLLING_INTERVAL']

client_id = f'python-mqtt-{random.randint(0, 1000)}'

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    # Set Connecting Client ID with callback_api_version
    client = mqtt_client.Client(client_id=client_id)

    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def on_disconnect(client, userdata, rc):
    logging.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)


def publish(client, value):
    time.sleep(1)
    msg = f"{value}"
    result = client.publish(topic, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{msg}` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")

def print_reg(register, client):
    print(register.description, register.format(), register.suffix)
    publish(client, register.format())

if __name__ == '__main__':
    from pysolarmanv5 import PySolarmanV5
    from deye_controller.modbus.sun_x_g3_registers import SunXG3Registers, SunXG3RegistersWrite

    client = connect_mqtt()
    client.loop_start()
    
    try:
        inv = PySolarmanV5(inverter_ip, inverter_sn)
    except KeyboardInterrupt:
        print("Program interrupted during initialization. Exiting gracefully...")
        client.loop_stop()
        print("Cleanup done. Program exited.")
        exit(0)
    
    try:
        while True:
            print_reg(SunXG3Registers.ACActivePower(inv), client)
            print()
            time.sleep(POLLING_INTERVAL)
    except KeyboardInterrupt:
        print("Program interrupted. Exiting gracefully...")
    finally:
        client.loop_stop()
        inv.disconnect()
        print("Cleanup done. Program exited.")