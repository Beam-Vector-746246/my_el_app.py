import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import urllib.parse

# Setup
st.set_page_config(page_title="Elpriser Silkeborg 2026", layout="centered")

def hent_el_data():
    BZN = "DK1"
    # Løser tidsfejlen: Vi tvinger appen til dansk tid (UTC+1)
    nu = datetime.now() + timedelta(hours=1) 
    
    st.title("⚡ Silkeborg El-Rapport")
    st.write(f"Opdateret: {nu.strftime('%d/%m %H:%M')}")

    # Hent data fra Energi Data Service
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=100"

    try:
        res = requests.get(url).json().get('records', [])
        
        # --- 2026 KONSTANTER (Alle priser EKSKL. MOMS) ---
        MOMS = 1.25
        AFGIFT = 0.008        # Lovpligtig afgift (0,01 kr m. moms)
        SYSTEM_TARIF = 0.115  # Energinet (0,14 kr m. moms)
        HANDEL = 0.050        # Dit elselskabs tillæg (ca. 0,06 kr m. moms)
        
        behandlet = []
        for r in res:
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            
            # Filtrér så vi kun ser fra nu og 24 timer frem
            if dt < nu.replace(minute=0, second=0, microsecond=0):
                continue
            
            h = dt.hour
            # N1 Vinter-tariffer 2026 (Ekskl. moms)
            if 17 <= h < 21:    
                tarif = 0.7907  # Spids (0,99 kr m. moms)
            elif 0 <= h < 6:    
                tarif = 0.0878  # Lav (0,11 kr m. moms)
            else:               
                tarif = 0.2636  # Høj (0,33 kr m. moms)
            
            # Beregning
            spot_kwh = r['DayAheadPriceDKK'] / 1000
            total = (spot_kwh + tarif + SYSTEM_TARIF + AFGIFT + HANDEL) * MOMS
            
            behandlet.append({
                'tid': dt, 
                'total': round(total, 2),
                'el': round(spot_kwh * MOMS, 2),
                'afgifter': round((tarif + SYSTEM_TARIF + AFGIFT + HANDEL) * MOMS, 2)
            })
        
        behandlet.sort(key=lambda x: x['tid'])

        if behandlet:
            nu_pris = behandlet[0]
            
            # Metrics
            c1, c2 = st.columns(2)
            c1.metric("Pris nu", f"{nu_pris['total']:.2f} kr")
            c2.metric("Heraf El", f"{nu_pris['el']:.2f} kr")

            # Graf
            fig, ax = plt.subplots(figsize=(10, 4))
            tider = [d['tid'] for d in behandlet[:24]]
            priser = [d['total'] for d in behandlet[:24]]
            ax.bar(tider, priser, color='#3498db', width=0.03)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
            plt.xticks(rotation=0)
            st.pyplot(fig)

            # Forklaring (ligesom din udbyder)
            st.info(f"""
            **Nedbrydning af prisen lige nu:**
            - **Ren El (Spot + Moms):** {nu_pris['el']} kr/kWh
            - **Tariffer & Afgifter:** {nu_pris['afgifter']} kr/kWh
            - **Total:** {nu_pris['total']} kr/kWh
            """)

    except Exception as e:
        st.error(f"Kunne ikke hente data: {e}")

if __name__ == "__main__":
    hent_el_data()
