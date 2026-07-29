"""
SCB ANALYS - Webbsida med Flask
Analyserar data hamtad fran SCB:s API for pagaende anstallningar med anstallningstid ≤6 manader
"""

from flask import Flask, render_template_string, request
import requests
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

# Funktion for att konvertera M-format till lasbart format
def konvertera_manad(manad_kod):
    """
    Konverterar t.ex. '2024M02' till 'Feb 2024'
    """
    try:
        ar = manad_kod[:4]
        manad_del = manad_kod[5:]  # Tar bort 'M' efter ar
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

# Funktion som genererar tillgängliga månader (senaste 24 månaderna)
def generera_tillgangliga_manader():
    """
    Genererar en lista med tillgängliga månader i formatet YYYY-MM
    för dropdown-menyn
    """
    manader = []
    idag = datetime.now()
    
    # Gå tillbaka 24 månader
    for i in range(48):
        datum = idag - timedelta(days=30*i)
        ar = datum.year
        manad = datum.month
        # Konvertera till SCB-format: YYYYMmm (t.ex. 2026M03)
        manad_kod = f"{ar}M{manad:02d}"
        manad_namn = konvertera_manad(manad_kod)
        manader.append({
            'kod': manad_kod,
            'namn': manad_namn
        })
    
    # Ta bort eventuella dubbletter och sortera
    unika_manader = []
    sedda_koder = set()
    for m in manader:
        if m['kod'] not in sedda_koder:
            sedda_koder.add(m['kod'])
            unika_manader.append(m)
    
    # Sortera så att nyaste månaden visas först
    return sorted(unika_manader, key=lambda x: x['kod'], reverse=True)

# Funktion som hamtar och bearbetar data
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
    
    # Mappning av koder till lasbara namn
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
        
        # Samla in data
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
        
        # Skapa tabell data
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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Analys av korta anstallningar (≤6 manader) fran SCB. Valj manad for att se statistik fordelat pa sektor, kon och totala antalet anstallningar.">
    <title>SCB Analys - Korta anstallningar</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #1a1a1a;
            line-height: 1.6;
        }
        h1 {
            color: #1a2a3a;
            border-bottom: 3px solid #1a6b8a;
            padding-bottom: 10px;
        }
        .container {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #1a1a1a;
        }
        select {
            padding: 8px;
            width: 250px;
            border: 1px solid #666666;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            background-color: #ffffff;
            color: #1a1a1a;
        }
        select:hover {
            border-color: #1a6b8a;
        }
        select:focus {
            outline: 2px solid #1a6b8a;
            outline-offset: 2px;
        }
        button {
            background-color: #1a6b8a;
            color: #ffffff;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            margin-left: 10px;
        }
        button:hover {
            background-color: #0d4a63;
        }
        button:focus {
            outline: 3px solid #0d4a63;
            outline-offset: 2px;
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .form-row {
            display: flex;
            align-items: flex-end;
            gap: 10px;
            flex-wrap: wrap;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #999999;
            padding: 12px;
            text-align: right;
        }
        th {
            background-color: #1a6b8a;
            color: #ffffff;
            text-align: center;
            font-weight: bold;
        }
        td:first-child, th:first-child {
            text-align: left;
        }
        .error {
            background-color: #8b1a1a;
            color: #ffffff;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
            border-left: 4px solid #ff4444;
        }
        .success {
            background-color: #1a6b3a;
            color: #ffffff;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
            border-left: 4px solid #44ff88;
        }
        .total {
            margin-top: 20px;
            padding: 15px;
            background-color: #e8eaed;
            border-radius: 4px;
            font-weight: bold;
            font-size: 18px;
            color: #1a1a1a;
            border-left: 4px solid #1a6b8a;
        }
        .info {
            margin-top: 10px;
            color: #333333;
            font-size: 12px;
        }
        .loading {
            display: none;
            margin-left: 10px;
            color: #1a6b8a;
            font-weight: bold;
        }
        main {
            outline: none;
        }
        a:focus, 
        button:focus,
        select:focus {
            outline: 3px solid #1a6b8a;
            outline-offset: 2px;
        }
    </style>
    <script>
        function showLoading() {
            document.getElementById('loading').style.display = 'inline';
            document.getElementById('submitBtn').disabled = true;
        }
    </script>
</head>
<body>
    <header role="banner" aria-label="Sidhuvud">
        <h1>SCB Analys - Korta anstallningar (≤6 manader)</h1>
    </header>
    
    <main role="main" id="main-content" aria-label="Huvudinnehall">
        <div class="container">
            <form method="POST" onsubmit="showLoading()" aria-label="Valj manad">
                <div class="form-group">
                    <label for="manad">Valj manad:</label>
                    <div class="form-row">
                        <select id="manad" name="manad" aria-required="true">
                            {% for manad in tillgangliga_manader %}
                            <option value="{{ manad.kod }}" {% if vald_manad == manad.kod %}selected{% endif %}>
                                {{ manad.namn }}
                            </option>
                            {% endfor %}
                        </select>
                        <button type="submit" id="submitBtn">Hamta data</button>
                        <span id="loading" class="loading">Laddar...</span>
                    </div>
                    <div class="info">Valj en manad fran listan for att visa statistik over korta anstallningar</div>
                </div>
            </form>
            
            {% if error %}
            <div class="error" role="alert">
                {{ error }}
            </div>
            {% endif %}
            
            {% if data %}
            <div class="success" role="status">
                Data for {{ data.manad_lasbar }}
            </div>
            
            <table aria-label="Statistik over korta anstallningar per sektor">
                <thead>
                    <tr>
                        <th scope="col">Sektor</th>
                        <th scope="col">Man</th>
                        <th scope="col">Kvinnor</th>
                        <th scope="col">Totalt</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rad in data.tabell_data %}
                    <tr>
                        <th scope="row">{{ rad.sektor }}</th>
                        {% if rad.visa_na %}
                        <td colspan="3" style="text-align: center; color: #333333;">N/A</td>
                        {% else %}
                        <td>{{ "{:,.0f}".format(rad.man) }}</td>
                        <td>{{ "{:,.0f}".format(rad.kvinna) }}</td>
                        <td><strong>{{ "{:,.0f}".format(rad.total) }}</strong></td>
                        {% endif %}
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            {% if data.total_alla > 0 %}
            <div class="total" role="status">
                TOTAL: {{ "{:,.0f}".format(data.total_alla) }} korta anstallningar i {{ data.manad_lasbar }}
            </div>
            {% endif %}
            {% endif %}
        </div>
    </main>
    
    <footer role="contentinfo" aria-label="Sidfot">
        <p style="margin-top: 20px; font-size: 14px; color: #333333; text-align: center;">
            Kalla: SCB<br>
            Data uppdateras lopande • Kontakta oss for fragor
        </p>
    </footer>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    # Generera lista med tillgängliga månader
    tillgangliga_manader = generera_tillgangliga_manader()
    
    # Standardvärde för vald månad
    vald_manad = '2026M03'
    
    if request.method == 'POST':
        vald_manad = request.form.get('manad', '2026M03')
        data, error = hamta_scb_data(vald_manad)
        return render_template_string(HTML_TEMPLATE, 
                                     data=data, 
                                     error=error,
                                     tillgangliga_manader=tillgangliga_manader,
                                     vald_manad=vald_manad)
    
    # GET request - visa utan data
    return render_template_string(HTML_TEMPLATE, 
                                 data=None, 
                                 error=None,
                                 tillgangliga_manader=tillgangliga_manader,
                                 vald_manad=vald_manad)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)  # ← debug=False i produktion
   
