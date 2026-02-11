import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import urllib.parse

# 1. Konfiguration
st.set_page_config(page_title="Silkeborg El-Rapport", layout="centered")

def hent_silkeborg_analyse():
    BZN = "DK1"
    
    # --- TIDSHÅNDTERING ---
    # Vi tvinger tiden til dansk tid (UTC+1)
    nu = datetime.utcnow() + timedelta(hours=1)
    
    # Vi finder det "aktive" kvarter (f.eks. 20:21 bliver til 20:15)
    aktuelt_kvarter = nu.replace(minute=(nu.minute // 15) * 15, second=0, microsecond=0)
    
    st.title("⚡ Silkeborg El-Rapport")
    st.write(f"Opdateret: {nu.strftime('%H:%M')} (Interval: {aktuelt_kvarter.strftime('%H:%M')})")

    # 2. Hent Spotpriser
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    spot_url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=200"

    try:
        res = requests.get(spot_url).json().get('records', [])
        
        # --- 2026 KONSTANTER (Ekskl. Moms) ---
        MOMS = 1.25
        AFGIFT = 0.008        
        SYSTEM_TARIF = 0.115  
        HANDEL = 0.040        
        
        behandlet = []
        for r in res:
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            
            # Vi inkluderer priser fra det kvarter vi er i lige nu
            if dt < aktuelt_kvarter: 
                continue
            
            h = dt.hour
            # N1 Vinter-tariffer 2026 (Ekskl. moms)
            if 17 <= h < 21:    
                tarif = 0.7500  # Spids (Giver 1.14 kr i alt m. afgifter/moms)
            elif 0 <= h < 6:    
                tarif = 0.0880  # Lav
            else:               
                tarif = 0.2640  # Høj
            
            spot_kwh = r['DayAheadPriceDKK'] / 1000
            
            # Beregnings-dele
            ren_el_moms = round(spot_kwh * MOMS, 2)
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
            # Nu peger behandlet[0] altid på det aktive kvarter
            nu_data = behandlet[0]
            
            col1, col2 = st.columns(2)
            col1.metric("Pris nu", f"{nu_data['pris']:.2f} kr")
            
            # Snit for de næste 24 timer
            p_24 = behandlet[:96]
            gns_pris = sum(d['pris'] for d in p_24) / len(p_24)
            col2.metric("Snit (næste 24t)", f"{gns_pris:.2f} kr")

            # --- GRAF ---
            fig, ax1 = plt.subplots(figsize=(10, 5))
            plt.style.use('bmh')
            
            x_vals = [d['tid'] for d in p_24]
            y_vals = [d['pris'] for d in p_24]
            
            # Marker nuværende time med en anden farve
            farver = ['#2980b9'] * len(y_vals)
            farver[0] = '#e74c3c' # Den røde bar er "lige nu"
            
            ax1.bar(x_vals, y_vals, color=farver, width=0.008)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            st.pyplot(fig)
            
            # Detalje-boks
            st.info(f"""
            **Lige nu ({nu_data['tid'].strftime('%H:%M')} - {(nu_data['tid'] + timedelta(minutes=15)).strftime('%H:%M')}):**
            - Ren el: {nu_data['el']:.2f} kr
            - Tariffer/Afgift: {nu_data['afgifter']:.2f} kr
            """)
            
    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    hent_silkeborg_analyse()
