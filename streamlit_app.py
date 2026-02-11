import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import urllib.parse
from collections import defaultdict

# Page configuration for mobile view
st.set_page_config(page_title="Elpriser Silkeborg", layout="centered")

def hent_silkeborg_analyse():
    BZN = "DK1"
    # Løser tidszone og runder ned til det aktuelle kvarter
    nu = datetime.utcnow() + timedelta(hours=1)
    aktuelt_kvarter = nu.replace(minute=(nu.minute // 15) * 15, second=0, microsecond=0)
    
    st.title("⚡ Silkeborg El-Rapport")
    st.write(f"Opdateret: {nu.strftime('%d/%m %H:%M')} (Interval: {aktuelt_kvarter.strftime('%H:%M')})")

    # 1. Hent Spotpriser
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    spot_url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=300"

    try:
        res = requests.get(spot_url).json().get('records', [])
        
        MOMS = 1.25
        AFGIFT = 0.008        # Lovpligtig afgift 2026
        SYSTEM_TARIF = 0.115  # Energinet 2026
        HANDEL = 0.040        # Tillæg til udbyder
        
        behandlet = []
        for r in res:
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            
            # Vi starter fra det kvarter vi er i lige nu
            if dt < aktuelt_kvarter: continue
            
            h = dt.hour
            # Præcise N1 2026 vinter-tariffer (ekskl. moms)
            if 17 <= h < 21:    tarif = 0.7907  # Spidslast (0,99 kr m. moms)
            elif 0 <= h < 6:    tarif = 0.0878  # Lavlast (0,11 kr m. moms)
            else:               tarif = 0.2636  # Højlast (0,33 kr m. moms)
            
            # Beregning der matcher udbyder
            spot_kwh = r['DayAheadPriceDKK'] / 1000
            el_pris_moms = round(spot_kwh * MOMS, 2)
            afgifter_moms = round((tarif + SYSTEM_TARIF + AFGIFT + HANDEL) * MOMS, 2)
            total_pris = round(el_pris_moms + afgifter_moms, 2)
            
            behandlet.append({
                'tid': dt, 
                'pris': total_pris, 
                'el': el_pris_moms, 
                'afgifter': afgifter_moms
            })
        
        behandlet.sort(key=lambda x: x['tid'])

        if behandlet:
            p_24 = behandlet[:96]
            x, y = [d['tid'] for d in p_24], [d['pris'] for d in p_24]
            gns_pris = sum(y) / len(y)

            # Metrics
            col1, col2 = st.columns(2)
            col1.metric("Pris nu", f"{behandlet[0]['pris']:.2f} kr")
            col2.metric("Snit (24t)", f"{gns_pris:.2f} kr")

            # --- VISUALISERING (Gensabt med farver og labels) ---
            fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
            plt.style.use('bmh')

            # Farvekodning som før
            farver = ['#e74c3c' if v > gns_pris * 1.15 else ('#2ecc71' if v < gns_pris * 0.85 else '#f1c40f') for v in y]
            ax1.bar(x, y, color=farver, width=0.008)
            ax1.axhline(gns_pris, color='black', linestyle='--', alpha=0.6)

            # Timelige gennemsnit labels (Genskabt)
            time_grupper = defaultdict(list)
            for d in p_24:
                time_grupper[d['tid'].hour].append(d['pris'])
            
            for hour, prices in time_grupper.items():
                # Find midter-tidspunktet for timen til label-placering
                label_tid = aktuelt_kvarter.replace(hour=hour, minute=30)
                if label_tid in x:
                    time_gns = sum(prices) / len(prices)
                    ax1.text(label_tid, max(y) * 1.02, f"{time_gns:.2f}", 
                            ha='center', fontsize=7, weight='bold',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

            ax1.set_ylabel("kr/kWh (inkl. moms/tarif)")
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            st.pyplot(fig)
            
            # Detalje-info (Nyt men vigtigt for at tjekke mod udbyder)
            st.info(f"""
            **Nedbrydning af prisen lige nu:**
            - Ren el (Spot + moms): **{behandlet[0]['el']:.2f} kr**
            - Afgifter, transport & handel: **{behandlet[0]['afgifter']:.2f} kr**
            """)
            
    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    hent_silkeborg_analyse()
