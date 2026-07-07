Créer un fichier .env à la racine du projet avec ces parametres :


- POSTGRES_USER=
- POSTGRES_PASSWORD=
- POSTGRES_DB=
- POSTGRES_HOST=
- POSTGRES_PORT=
- POSTGRES_SCHEMAS=



Documentation de l’API Stations / Tronçons


1. Récupérer les informations d’une station

Endpoint : GET /stations/{codestation}

Description :
Permet d’obtenir toutes les informations détaillées d’une station spécifique à partir de son code unique.

Retour attendu :

- Identifiant de la station
- Coordonnées géographiques (X, Y)
- Commune et département
- Type et nature de la station
- Code et nom du cours d’eau associé
- Région et autres attributs descriptifs


Usage métier :

Parfait pour obtenir la fiche complète d’une station et l’utiliser dans une analyse ou un affichage cartographique.

2. Trouver les stations amont et aval à partir d’une station

Endpoint : GET /stations/{codestation}/related_stations

Description :
Permet de découvrir les stations situées en amont et en aval d’une station donnée, en suivant le réseau hydrographique.

Retour attendu :

- Liste de stations amont avec leurs coordonnées et distance par rapport au tronçon
- Liste de stations aval avec les mêmes informations


Usage métier :

Utile pour analyser le réseau de suivi hydrologique, planifier des interventions, ou suivre la propagation d’événements sur le réseau (crues, pollution, etc.).

3. Trouver les stations amont et aval à partir d’un tronçon

Endpoint : GET /troncons/{troncon_id}/related_stations

Description :

Identique à la précédente, mais on part d’un tronçon de rivière plutôt que d’une station.

Retour attendu :


- Stations en amont et en aval du tronçon donné


Usage métier :

Permet d’explorer le réseau hydrographique à partir de tronçons connus, utile pour cartographie ou analyse du réseau.

4. Récupérer les tronçons amont et aval à partir d’un tronçon

Endpoint : GET /troncons/{troncon_id}/graph_tronconh

Description :
Permet de récupérer la liste des tronçons situés en amont et en aval d’un tronçon donné.

Retour attendu :


- Tronçons amont et aval au format GeoJSON (prêt à être affiché sur une carte)


Usage métier :

Utile pour visualiser le réseau hydrographique ou pour des calculs sur la connectivité du réseau.

5. Récupérer les tronçons amont et aval à partir d’une station

Endpoint : GET /troncon/{codestation}/graph_tronconh

Description :
Même fonction que le précédent, mais on part d’une station plutôt que d’un tronçon.

Retour attendu :


- Tronçons amont et aval liés à la station, au format GeoJSON

Usage métier :

Permet d’analyser le réseau à partir d’un point de mesure spécifique (station) et d’afficher les tronçons liés sur une carte.

6. Obtenir la route directes entre deux stations

Endpoint : GET stations/between_stations?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}

Endpoint : GET troncon/between_graph_tronconh?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}

Retour attendues :

- Tronçons et statiosn entre deux points (stations)

Usage métier : cela peut permettre la sélection en ligne directe amont/aval 


7. Fonctions internes principales (métier)


- get_troncons_for_station(codestation) : retrouve les tronçons liés à une station.
- resolve_troncon_id_from_idtronconh(idtronconh) : traduit l’identifiant externe d’un tronçon en identifiant interne utilisé pour l’analyse du réseau.
- get_upstream_sections(troncon_id) : récupère tous les tronçons en amont d’un tronçon donné.
- get_downstream_sections(troncon_id) : récupère tous les tronçons en aval d’un tronçon donné.
- get_matching_stations(upstream_df) : relie les tronçons récupérés aux stations présentes dessus, en ajoutant la distance par rapport 
au tronçon.    
- get_matching_section_id(stream_df) : récupère les informations des tronçons, y compris leur géométrie, pour pouvoir les représenter sur une carte.
- get_geodf_between2_stations : Obtenir la route directes entre deux stations



Usage métier :
Ces fonctions permettent de naviguer dans le réseau hydrographique, de relier stations et tronçons, et de préparer les données pour l’affichage ou l’analyse métier (cartographie, suivi du réseau, étude des distances et connexions).
