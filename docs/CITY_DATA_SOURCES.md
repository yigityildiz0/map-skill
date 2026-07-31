# Official city data sources

Verified: **2026-07-31**. This is a compact index; the machine-readable registry contains the complete use/limit/licence notes.

Legend: 🟢 no key · 🟡 free registration/API key · 🔵 official web check · ⚠️ material coverage/terms caveat

| City | Transit baseline | Realtime/status | Traffic/closures | Key limitation |
|---|---|---|---|---|
| **İstanbul** | 🟢 [İETT GTFS](https://data.ibb.gov.tr/api/3/action/package_show?id=iett-gtfs-verisi) | 🟢 [Metro status API](https://api.ibb.gov.tr/MetroIstanbul/api/MetroMobile/V2/GetServiceStatuses); tested IETT alert/vehicle SOAP methods are no-key, other methods are conditional; 🔵 [ferry cancellations](https://sehirhatlari.istanbul/tr/iptal-seferler) | 🟢/🔵 [IBB traffic map](https://uym.ibb.gov.tr/yharita6/) | ⚠️ No verified citywide standard GTFS-RT; IETT live data is not GTFS-RT and any authentication failure is `no_data`. |
| **London** | 🟡 [TfL open data](https://tfl.gov.uk/info-for/open-data-users/our-open-data) | 🟡 [TfL Unified API](https://tfl.gov.uk/info-for/open-data-users/unified-api), 🔵 [status](https://tfl.gov.uk/status-updates/) | 🔵 [TfL traffic](https://tfl.gov.uk/traffic/status) | ⚠️ Keep timestamps; road coverage is not uniform across every borough road. |
| **Paris / Île-de-France** | 🟡 [IDFM GTFS](https://prim.iledefrance-mobilites.fr/jeux-de-donnees/offre-horaires-tc-gtfs-idfm) | 🟡 [SIRI Lite](https://prim.iledefrance-mobilites.fr/fr/apis/idfm-ivtr-requete_ligne) | 🔵 [Sytadin](https://www2.sytadin.fr/) | ⚠️ Realtime does not cover every line; check the official coverage list. |
| **Berlin / Brandenburg** | 🟢 [VBB GTFS](https://unternehmen.vbb.de/digitale-services/datensaetze/) | 🟢 [VBB GTFS-RT](https://production.gtfsrt.vbb.de/data) | 🔵 [VIZ Berlin](https://viz.berlin.de/) | ⚠️ VBB reported GTFS-RT data loss/incomplete coverage from 2026-06-04 at verification time. |
| **Dublin** | 🟢 [NTA GTFS](https://www.transportforireland.ie/transitData/Data/GTFS_All.zip) | 🟡 [NTA GTFS-R v2](https://api.nationaltransport.ie/gtfsr/v2/gtfsr?format=json) | 🔵 [TII Traffic](https://traffic.tii.ie/) | ⚠️ Exclude the old frozen TII DATEX travel-time XML from live evidence. |
| **Milano** | 🟢 [Comune/AMAT GTFS](https://dati.comune.milano.it/dataset/ds929-orari-del-trasporto-pubblico-locale-nel-comune-di-milano-in-formato-gtfs) | 🔵 [ATM traffic info](https://www.atm.it/IT/VIAGGIACONNOI/INFOTRAFFICO/Pagine/default2.aspx) | 🔵 official/partner web validation | ⚠️ No verified openly licensed machine-readable GTFS-RT/SIRI feed. |
| **Madrid** | 🟢 [CRTM open data](https://transparencia.crtm.es/presupuestos-contratos-y-gastos/datos-abiertos/?lang=es) | 🟡 [EMT realtime](https://datos.emtmadrid.es/es/dataset/tiempo-real-para-autobuses-de-emt) | 🟢 [DGT incidents](https://nap.dgt.es/es/dataset/incidencias-dgt-datex2-v3-7) | ⚠️ EMT evidence covers city buses, not the whole regional network. |
| **Tokyo** | 🟡 [ODPT Tokyo Metro GTFS](https://ckan.odpt.org/en/dataset/train-tokyometro) | 🟡 [ODPT Toei GTFS-RT](https://ckan.odpt.org/en/dataset/r_train_gtfs_rt-odpt_train-toei) | 🔵 [JARTIC](https://www.jartic.or.jp/) | ⚠️ Operator-partial; JARTIC live web content must not be scraped/republished. |
| **Seoul** | 🟡 [Seoul transit APIs](https://data.seoul.go.kr/dataList/OA-22750/A/1/datasetView.do) | 🟡 [subway arrival API](https://data.seoul.go.kr/dataList/OA-12764/A/1/datasetView.do) | 🟡/🔵 [TOPIS](https://topis.seoul.go.kr/) | ⚠️ No verified citywide GTFS; TOPIS has stricter non-profit API language. |
| **Singapore** | 🟡 [LTA DataMall](https://datamall.lta.gov.sg/content/datamall/en/dynamic-data.html) | 🟡 BusArrival/TrainServiceAlerts, 🔵 [train status](https://mytransport.sg/trainstatus) | 🟡 DataMall, 🔵 [OneMotoring](https://onemotoring.lta.gov.sg/content/onemotoring/home/driving/traffic_information/traffic_updates_and_road_closures.html) | ⚠️ No complete public MRT timetable/next-train API. |
| **Hong Kong** | 🟢 [Transport Department GTFS](https://data.gov.hk/en-datasets/search/Public%20Transport) | 🟢 [MTR next train](https://data.gov.hk/en-data/dataset/mtr-data2-nexttrain-data) and operator ETAs | 🟢 [strategic road traffic](https://data.gov.hk/en-data/dataset/hk-td-sm_4-traffic-data-strategic-major-roads) | ⚠️ Some modes are headway-based and small operators may be missing. |
| **Toronto** | 🟢 [TTC GTFS](https://open.toronto.ca/dataset/ttc-routes-and-schedules/) | 🟢 [TTC GTFS-RT](https://gtfsrt.ttc.ca/) | 🟢 [road restrictions](https://open.toronto.ca/dataset/road-restrictions/) | ⚠️ Dataset licence fields were unspecified; retrieve/attribute at runtime, do not bundle. |
| **New York City** | 🟢 [MTA developer feeds](https://www.mta.info/developers) | 🟢/🟡 [MTA realtime](https://api.mta.info/), [Bus Time](https://bt.mta.info/developers) | 🟢/🔵 [NYC DOT feeds](https://www.nyc.gov/html/dot/html/about/datafeeds.shtml) | ⚠️ MTA terms prohibit direct end-user serving from MTA servers; use a compliant proxy or passenger page. |
| **Chicago** | 🟢 [CTA GTFS](https://www.transitchicago.com/developers/gtfs/) | 🟡 [CTA GTFS-RT](https://transitdata.transitchicago.com/), 🔵 [alerts](https://www.transitchicago.com/alerts/) | 🔵 [IDOT closures](https://idot.illinois.gov/travel-and-maps/roadways/road-closures.html) | ⚠️ Chicago Traffic Tracker was stale at verification time and is excluded as live. |
| **Mexico City** | 🟢 [SEMOVI GTFS](https://datos.cdmx.gob.mx/dataset/gtfs) | 🟡 [Metrobús realtime](https://metrobus.cdmx.gob.mx/portal-ciudadano/datos-abiertos), 🔵 [Metro status](https://www.metro.cdmx.gob.mx/la-red/estado-del-servicio) | 🔵 SSC/Orientador Vial | ⚠️ Validate feed dates; realtime is operator-partial and INFOVIAL open data is historical. |
| **Sydney** | 🟡 [Transport for NSW Complete GTFS](https://opendata.transport.nsw.gov.au/data/dataset/timetables-complete-gtfs) | 🟡 [GTFS-RT v2](https://opendata.transport.nsw.gov.au/dataset/public-transport-realtime-trip-update-v2) | 🟡 [Live Traffic Hazards](https://opendata.transport.nsw.gov.au/data/dataset/live-traffic-hazards) | ⚠️ Free account/token required; prefer explicitly CC-labelled resources. |

## Universal fallback outside these cities

The absence of a city profile does not disable Map Skill. It changes confidence and source selection:

1. exact official operator journey planner and passenger status;
2. current accessible route-provider alternatives;
3. official municipal/regional traffic and event pages;
4. verified GTFS/GTFS-Realtime discovered through first-party sources;
5. weather/opening checks;
6. explicit partial/unknown coverage note.

Do not treat a feed catalog entry as proof that a feed is current or licensed for the intended use.
