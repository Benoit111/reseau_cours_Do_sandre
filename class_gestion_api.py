class api_courdo():
    '''
    Cette classe permet la lecture de l 'api_courdo et 
    la mise ne forme des retours json vers des DataFrame pandas ou geopanda
    '''
    
    ENDPOINT_STATION = "stations/{codestation}"
    ENDPOINT_RELATED_BY_STATION = "stations/{codestation}/related_stations"
    ENDPOINT_RELATED_BY_TRONCON = "troncons/{troncon_id}/related_stations"
    ENDPOINT_GRAPH_BY_TRONCON = "troncons/{troncon_id}/graph_tronconh"
    ENDPOINT_GRAPH_BY_STATION = "troncon/{codestation}/graph_tronconh"
    ENDPOINT_GRAPH_BY_STATION = "troncon/{codestation}/graph_tronconh"
    ENDPOINT_BETWEEN_BY_STATION = "between/stations?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}"
    ENDPOINT_BETWEEN_BY_TRONCON = "between/graph_tronconh?codestation_amont={codestation_amont}&codestation_aval={codestation_aval}"
    

    def __init__(self,base_url):
        self.base_url=base_url

    def assertJsonSuccess(self, response):
        try:
            obj = response.json()
            if isinstance(obj, dict) and obj.get("status") == "errors":
                print("Erreur API:", obj)
                return False
        except Exception:
            return True
        return True

    def build_requet(self, endpoint):
        """Lit le JSON et retourne des DataFrame GeoDataFrame ou pandas selon le contenu"""
        try:
            url = f'{self.base_url}/{endpoint}'
            print(url)
            response = requests.get(url)
            
            if response.status_code in [404, 500]:
                print(f"Ressource ou code référentiel non trouvée pour {url}")
                return pd.DataFrame(), pd.DataFrame()
            if response.status_code != 200:
                print(f"Erreur sur le retour de requête - statut : {response.status_code}")
                return pd.DataFrame(), pd.DataFrame()
    
            if not self.assertJsonSuccess(response):
                return None
    
            data = response.json()
            #print(data.keys() if isinstance(data, dict) else type(data))
    
            df_amont, df_aval = None, None
    
            # dictionnaire de clés possibles
            #amont_keys = ['amont_troncons', 'amont_stations']
            ##aval_keys = ['aval_troncons', 'aval_stations']
            amont_keys = ['amont_troncons', 'amont_stations', 'features']  
            aval_keys = ['aval_troncons', 'aval_stations']

            # et gérer le cas "stations" (liste simple) et FeatureCollection directe
            if 'stations' in data:
                return pd.DataFrame(data['stations']), pd.DataFrame()
            
            if 'type' in data and data['type'] == 'FeatureCollection':
                return gpd.GeoDataFrame.from_features(data['features']), pd.DataFrame()
                        # trouver la première clé existante
            amont_key = next((k for k in amont_keys if k in data), None)
            aval_key = next((k for k in aval_keys if k in data), None)
    
            # créer GeoDataFrame si c'est un FeatureCollection
            if amont_key and isinstance(data[amont_key], dict) and 'features' in data[amont_key]:
                df_amont = gpd.GeoDataFrame.from_features(data[amont_key]['features'])
                df_amont['sens'] = 'amont'
            elif amont_key:
                df_amont = pd.DataFrame(data[amont_key])
                df_amont['sens'] = 'amont'
    
            if aval_key and isinstance(data[aval_key], dict) and 'features' in data[aval_key]:
                df_aval = gpd.GeoDataFrame.from_features(data[aval_key]['features'])
                df_aval['sens'] = 'aval'
            elif aval_key:
                df_aval = pd.DataFrame(data[aval_key])
                df_aval['sens'] = 'aval'
    
            # si au moins un des deux DataFrame est créé, on les retourne
            if df_amont is not None or df_aval is not None:
                return df_amont, df_aval
    
            # si c'est une liste ou un dict simple
            if isinstance(data, list):
                return pd.DataFrame(data)
            if isinstance(data, dict):
                return pd.DataFrame([data])
            if isinstance(data, str):
                print(data)
                return data
    
            print(f'Erreur sur le retour de requête - statut : {response.status_code}')
            return None
    
        except requests.exceptions.RequestException as e:
            raise ValueError('Erreur sur la lecture du HTTP', e)
 



    def Read_Station(self,codestation):
        '''lecture des informations de la stations 
        codestation  string '''

        return self.build_requet(self.ENDPOINT_STATION.format(codestation=codestation))

    def get_Related_Stations_By_Station(self,codestation):
        '''retour  des stations présent sur le me^me réseau que de la station en paramètre
        codestation  string '''
        return self.build_requet(self.ENDPOINT_RELATED_BY_STATION.format(codestation=codestation))

    def get_Related_Stations_By_Troncon(self,troncon_id):
        '''retour  des stations présent sur le même réseau que de le troncon en paramètre
        troncon_id  string 
        return 2 DataFrame >>> amont - aval  '''
        return self.build_requet(self.ENDPOINT_RELATED_BY_TRONCON.format(troncon_id=troncon_id))

    def get_Related_Troncon_By_Troncons(self,troncon_id):
        '''retour  des troncons présent sur le même réseau que de le troncon en paramètre
        troncon_id  string 
        return 2 DataFrame >>> amont - aval'''
        return self.build_requet(self.ENDPOINT_GRAPH_BY_TRONCON.format(troncon_id=troncon_id))

    def get_Related_Troncon_By_Station(self,codestation):
        '''retour  des tronçons présent sur le même réseau que de la station en paramètre
        codestation string 
        return 2 DataFrame >>> amont - aval  '''
        return self.build_requet(self.ENDPOINT_GRAPH_BY_STATION.format(codestation=codestation))
        
    def get_between_By_Station(self,codestation_amont,codestation_aval):
       '''retour  des stations entre la station amont et la station aval en paramètre
       codestation string 
       return 2 DataFrame >>> amont - aval  '''
       return self.build_requet(self.ENDPOINT_BETWEEN_BY_STATION.format(codestation_amont=codestation_amont,codestation_aval=codestation_aval))

    def get_between_By_Troncon(self,codestation_amont,codestation_aval):
       '''retour  des tronçons entre la station amont et la staion aval en paramètre
       codestation string 
       return 2 DataFrame >>> amont - aval  '''
       return self.build_requet(self.ENDPOINT_BETWEEN_BY_TRONCON.format(codestation_amont=codestation_amont,codestation_aval=codestation_aval))
