import requests

api_key="4fa221e40fa0935eb478acfd7ea2c6f4"

#base url da Api
base_url = "http://api.openweathermap.org/data/2.5/weather?"

#definir a cidade que queremos
city_name = "Braga"

#passar a temp para graus celsius
graus = "&units=metric"

#formar o url do pedido
full_url = base_url + "appid=" + api_key + "&q=" + city_name + graus

#enviar o pedido para o servidor do open weather maps
response = requests.get(full_url)

#transforma a resposta da Api em dicionario python
x = response.json()

if x["cod"] == 200:
    y = x["main"]
    current_temperature = y["temp"]
    current_pressure = y["pressure"]
    current_humidity = y["humidity"]
    z = x["weather"]

    weather_description = z[0]["description"]

    print("Temperatura = " + str(current_temperature) + 
    "\n Atmospheric pressure (hPa) = " + str(current_pressure) +
    "\n Humidity (in percentage) = " + str(current_humidity) +
    "\n Weatherdescription = " + str(weather_description))

else:
    print("Cidade não encontrada")

