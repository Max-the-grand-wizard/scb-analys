"""
SCB ANALYS - Webbsida med Flask
Analyserar data hamtad fran SCB:s API for pagaende anstallningar med anstallningstid ≤6 manader
"""

from flask import Flask, render_template, request
import requests
import pandas as pd
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Funktion for att konvertera M-format till lasbart format
def konvertera_manad(manad_kod):
    try:
        ar = manad_kod[:4]
        manad_del = manad_kod[5:]
        manad_nummer = int(manad_del)
        manader = {
            1: "Jan", 2: "Feb", 3: "Mar",
            4: "Apr", 5: "Maj", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep",
            10: "Okt", 11: "Nov", 12: "Dec"
        }
        manad_namn = manader.get(manad_nummer, "???")
        return f"{manad_namn} {ar}"
    except:
        return manad_kod

def generera_tillgangliga_manader():
    manader = []
    idag = datetime.now()
    for i in range(48):
        datum = idag - timedelta(days=30*i)
        ar = datum.year
        manad = datum.month
        manad_kod = f"{ar}M{manad:02d}"
        manad_namn = konvertera_manad(manad_kod)
        manader.append({
            'kod': manad_kod,
            'namn': manad_namn
        })
    unika_manader = []
    sedda_koder = set()
    for m in manader:
        if m['kod'] not in sedda_koder:
            sedda_koder.add(m['kod'])
            unika_manader.append(m)
    return sorted(unika_manader, key=lambda x: x['kod'], reverse=True)

def hamta_scb_data(manad_kod):
    url = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AM/AM0211/AM0211A/PagaendeAnstAnstTid"
    query = {
        "query": [
            {
                "code": "ContentsCode",
                "selection": {
                    "filter": "all",
                    "values": ["*"]
                }
            },
            {
                "code": "Tid",
                "selection": {
                    "filter": "item",
                    "values": [manad_kod]
                }
            }
        ],
        "response": {
            "format": "json"
        }
    }
    sektor_mappning = {
        "010": "Samtliga sektorer",
        "030": "Näringslivet",
        "320": "Staten",
        "409": "Region",
        "410": "Kommun",
        "040": "Hushållens organisationer"
    }
    kon_mappning = {
        "1": "Män",
        "2": "Kvinnor",
        "1+2": "Totalt"
    }
    try:
        response = requests.post(url, json=query, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'data' not in data or len(data['data']) == 0:
            return None, f"Ingen data hittades för {konvertera_manad(manad_kod)}"
        resultat = []
        for item in data['data']:
            sektor_kod = item['key'][0]
            kon_kod = item['key'][1]
            if kon_kod == "1+2":
                continue
            if len(item['values']) > 2:
                antal_kort = item['values'][2]
                try:
                    antal = int(antal_kort) if antal_kort and antal_kort.isdigit() else 0
                except (ValueError, TypeError):
                    antal = 0
                resultat.append({
                    'sektor': sektor_mappning.get(sektor_kod, sektor_kod),
                    'kon': kon_mappning.get(kon_kod, kon_kod),
                    'antal': antal
                })
        if len(resultat) == 0:
            return None, f"Ingen användbar data hittades för {konvertera_manad(manad_kod)}"
        df = pd.DataFrame(resultat)
        sektor_ordning = ["Samtliga sektorer", "Näringslivet", "Staten", "Region", "Kommun", "Hushållens organisationer"]
        tabell_data = []
        total_alla = 0
        for sektor in sektor_ordning:
            man_data = df[(df['sektor'] == sektor) & (df['kon'] == 'Män')]['antal'].values
            kvinna_data = df[(df['sektor'] == sektor) & (df['kon'] == 'Kvinnor')]['antal'].values
            man = man_data[0] if len(man_data) > 0 else 0
            kvinna = kvinna_data[0] if len(kvinna_data) > 0 else 0
            total = man + kvinna
            if sektor == "Samtliga sektorer":
                total_alla = total
            tabell_data.append({
                'sektor': sektor,
                'man': man,
                'kvinna': kvinna,
                'total': total,
                'visa_na': (man == 0 and kvinna == 0 and sektor != "Samtliga sektorer")
            })
        return {
            'tabell_data': tabell_data,
            'manad_lasbar': konvertera_manad(manad_kod),
            'total_alla': total_alla
        }, None
    except Exception as e:
        return None, f"Fel vid anslutning till SCB: {str(e)}"

@app.route('/', methods=['GET', 'POST', 'HEAD'])
def index():
    # Hantera HEAD-förfrågningar (används av Render för health checks)
    if request.method == 'HEAD':
        return '', 200
    
    tillgangliga_manader = generera_tillgangliga_manader()
    vald_manad = '2026M03'
    
    if request.method == 'POST':
        vald_manad = request.form.get('manad', '2026M03')
        data, error = hamta_scb_data(vald_manad)
        return render_template('index.html', 
                             data=data, 
                             error=error,
                             tillgangliga_manader=tillgangliga_manader,
                             vald_manad=vald_manad)
    
    return render_template('index.html', 
                         data=None, 
                         error=None,
                         tillgangliga_manader=tillgangliga_manader,
                         vald_manad=vald_manad)

@app.route('/debug')
def debug():
    import os
    info = {
        'current_directory': os.getcwd(),
        'files_in_current': os.listdir('.'),
        'templates_exists': os.path.exists('templates'),
        'templates_files': os.listdir('templates') if os.path.exists('templates') else 'Finns inte',
        'app_root': app.root_path,
        'template_folder': app.template_folder
    }
    return info

@app.route('/test')
def test():
    return "Hello World! Appen fungerar!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)