import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import urllib.parse
from collections import defaultdict

# 1. Konfiguration
st.set_page_config(page_title="Silkeborg El-Rapport", layout="centered")

def hent_silkeborg_analyse():
    BZN = "DK1"
    
    # Håndtering af tidszone (Streamlit Cloud kører ofte UTC)
    # Vi tjekker om vi skal lægge 1 time til for at ramme dansk tid
    nu_utc = datetime.utcnow()
    nu = nu_utc + timedelta(hours=1) 
    
    st.title("⚡ Silkeborg El-Rapport")
    st.write(f"Opdateret: {nu.strftime('%d/%m %H:%M')}")

    # 2. Hent Spotpriser
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    spot_url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=200"

    try:
        res = requests.get(spot_url).json().get('records', [])
        
        # --- 2026 KONSTANTER (Ekskl. Moms) ---
        MOMS = 1.25
        AFGIFT = 0.008        # Lovpligtig elafgift 2026
        SYSTEM_TARIF = 0.115  # Energinet Systemtarif 2026
        HANDEL = 0.040        # Estimeret tillæg til elselskab
        
        behandlet = []
        for r in res:
            # Konverter TimeDK til datetime objekt
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            
            # Vi viser priser fra starten af nuværende time
            if dt < nu.replace(minute=0, second=0, microsecond=0): 
                continue
            
            h = dt.hour
            # N1 Vinter-tariffer 2026 (Ekskl. moms)
            # Disse værdier + SYSTEM_TARIF + AFGIFT + HANDEL * 1.25 giver ca. 1.14 kr.
            if 17 <= h < 21:    
                tarif = 0.7500  # Spidslast
            elif 0 <= h < 6:    
                tarif = 0.0880  # Lavlast
            else:               
                tarif = 0.2640  # Højlast
            
            spot_kwh = r['DayAheadPriceDKK'] / 1000
            
            # Udregning af de to dele som din udbyder viser
            ren_el_moms = round(spot_kwh * MOMS, 2)
            # Vi justerer handels-tillæg her så det lander på de 1.14 kr i alt for tariffer
            afgifter_moms = round((tarif + SYSTEM_TARIF + AFGIFT + HANDEL) * MOMS, 2)
            total_pris = round(ren_el_moms + afgifter_moms, 2)
            
            behandlet.append({
                'tid': dt, 
                'pris': total_pris, 
                'el': ren_el_moms, 
                'afgifter': afgifter_moms
            })
        
        behandlet.sort(key=lambda x: x['tid'])

        if behandlet:
            # Data til visning
            nu_data = behandlet[0]
            p_24 = behandlet[:96] # 15-min intervaller
            x = [d['tid'] for d in p_24]
            y = [d['pris'] for d in p_24]
            gns_pris = sum(y) / len(y)

            # Metrics
            col1, col2 = st.columns(2)
            col1.metric("Pris nu", f"{nu_data['pris']:.2f} kr")
            col2.metric("Snit (24t)", f"{gns_pris:.2f} kr")

            # --- VISUALISERING ---
            fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
            plt.style.use('bmh')

            # Farver baseret på gennemsnit
            farver = ['#e74c3c' if v > gns_pris * 1.10 else ('#2ecc71' if v < gns_pris * 0.90 else '#f1c40f') for v in y]
            ax1.bar(x, y, color=farver, width=0.008)
            ax1.axhline(gns_pris, color='black', linestyle='--', alpha=0.5)

            # Formatering
            ax1.set_ylabel("kr/kWh (inkl. moms/tarif)")
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            st.pyplot(fig)
            
            # Detaljeret info (matcher din udbyder)
            st.write(f"### Detaljer for kl. {nu_data['tid'].strftime('%H:%M')}")
            st.write(f"- **Ren el (Spot + Moms):** {nu_data['el']:.2f} kr")
            st.write(f"- **Tariffer & Afgifter:** {nu_data['afgifter']:.2f} kr")
            st.write(f"**Total pris: {nu_data['pris']:.2f} kr**")
            
    except Exception as e:
        st.error(f"Der skete en fejl: {e}")

if __name__ == "__main__":
    hent_silkeborg_analyse()
