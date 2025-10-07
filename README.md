1. Calcul de l'Oscillateur
Calcule un PPO basé sur le prix de clôture (close). La formule est : ((MME rapide - MME lente) / MME lente) * 100.

Lisse le PPO calculé en utilisant une moyenne mobile simple (MMS). Le résultat sera la ligne principale de l'oscillateur.

2. Paramètres Configurables par l'Utilisateur
L'utilisateur doit pouvoir modifier les paramètres suivants :

Longueur de la Moyenne Mobile Exponentielle (MME) rapide (défaut : 12).

Longueur de la MME lente (défaut : 26).

Période de lissage pour le PPO (défaut : 2).

Une case à cocher pour activer/désactiver les divergences à long terme (défaut : activé).

Une période de recherche (Lookback Period) pour ces divergences à long terme (défaut : 55).

3. Logique de Détection de Divergence
Identifier les points pivots :

Détecte les creux (bottoms) sur le prix (plus bas) et sur l'oscillateur PPO.

Détecte les sommets (tops) sur le prix (plus hauts) et sur l'oscillateur PPO.

Assure-toi que la détection des pivots sur le prix fonctionne même si le prix stagne sur plusieurs bougies (plateaux).

Définir les conditions de divergence :

Divergence Haussière (Bullish) Classique : Le prix forme un creux plus bas que le précédent, tandis que l'oscillateur forme un creux plus haut.

Divergence Baissière (Bearish) Classique : Le prix forme un sommet plus haut que le précédent, tandis que l'oscillateur forme un sommet plus bas.

Gérer les cas spécifiques :

Inclus une logique pour détecter les divergences où le pivot du prix apparaît légèrement en retard (moins de 3 bougies) par rapport au pivot de l'oscillateur.

Si l'option "long term Divergences" est activée, ajoute une vérification de divergence en comparant le pivot actuel avec le plus haut/bas absolu du prix et de l'oscillateur sur la Lookback Period définie.
