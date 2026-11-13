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

# Funktion som hämtar alla giltiga månadskoder från SCB:s metadata
def hamta_giltiga_manader():
    """
    Hämtar alla giltiga månadskoder för Tid från SCB:s metadata
    och returnerar en lista med dicts {'kod': ..., 'namn': ...},
    nyaste månaden först.
    """
    url = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AM/AM0211/AM0211A/PagaendeAnstAnstTid"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        meta = r.json()
        for var in meta.get("variables", []):
            if var["code"] == "Tid":
                giltiga = var["values"]
                resultat = []
                for kod in giltiga:
                    resultat.append({
                        'kod': kod,
                        'namn': konvertera_manad(kod)
                    })
                return sorted(resultat, key=lambda x: x['kod'], reverse=True)
    except Exception as e:
        print(f"Kunde inte hämta giltiga månader: {e}")
    return []

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

# HTML-mall för webbsidan
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>SCB Analys - Korta anställningar</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .container {
            background-color: white;
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
            color: #2c3e50;
        }
        select {
            padding: 8px;
            width: 250px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
        }
        select:hover {
            border-color: #3498db;
        }
        button {
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
        }
        button:hover {
            background-color: #2980b9;
        }
        .form-row {
            display: flex;
            align-items: flex-end;
            gap: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: right;
        }
        th {
            background-color: #3498db;
            color: white;
            text-align: center;
        }
        td:first-child, th:first-child {
            text-align: left;
        }
        .error {
            background-color: #e74c3c;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
        }
        .success {
            background-color: #2ecc71;
            color: white;
            padding: 10px;
            border-radius: 4px;
            margin-top: 20px;
        }
        .total {
            margin-top: 20px;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 4px;
            font-weight: bold;
            font-size: 18px;
        }
        .info {
            margin-top: 10px;
            color: #7f8c8d;
            font-size: 12px;
        }
        .loading {
            display: none;
            margin-left: 10px;
            color: #3498db;
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
    <h1> SCB Analys - Korta anställningar (≤6 månader)</h1>
    
    <div class="container">
        <form method="POST" onsubmit="showLoading()">
            <div class="form-group">
                <label for="manad">Välj månad:</label>
                <div class="form-row">
                    <select id="manad" name="manad">
                        {% for manad in tillgangliga_manader %}
                        <option value="{{ manad.kod }}" {% if vald_manad == manad.kod %}selected{% endif %}>
                            {{ manad.namn }}
                        </option>
                        {% endfor %}
                    </select>
                    <button type="submit" id="submitBtn">Hämta data</button>
                    <span id="loading" class="loading">⏳ Laddar...</span>
                </div>
                <div class="info"> Välj en månad från listan för att visa statistik</div>
            </div>
        </form>
        
        {% if error %}
        <div class="error">
             {{ error }}
        </div>
        {% endif %}
        
        {% if data %}
        <div class="success">
             Data för {{ data.manad_lasbar }}
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Sektor</th>
                    <th>Män</th>
                    <th>Kvinnor</th>
                    <th>Totalt</th>
                </tr>
            </thead>
            <tbody>
                {% for rad in data.tabell_data %}
                <tr>
                    <td>{{ rad.sektor }}</td>
                    {% if rad.visa_na %}
                    <td colspan="3" style="text-align: center;">N/A</td>
                    {% else %}
                    <td>{{ "{:,.0f}".format(rad.man) }}</td>
                    <td>{{ "{:,.0f}".format(rad.kvinna) }}</td>
                    <td>{{ "{:,.0f}".format(rad.total) }}</td>
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        {% if data.total_alla > 0 %}
        <div class="total">
             TOTAL: {{ "{:,.0f}".format(data.total_alla) }} korta anställningar i {{ data.manad_lasbar }}
        </div>
        {% endif %}
        {% endif %}
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    # Generera lista med tillgängliga månader
    tillgangliga_manader = hamta_giltiga_manader()
    
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
   