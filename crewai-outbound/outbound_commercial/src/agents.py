from __future__ import annotations
from crewai import Agent

def build_agents():
    agent_commercial = Agent(
        role="Représentant commercial",
        goal="Identifier des prospects à forte valeur correspondant à l'ICP",
        backstory=("Radar stratégique pour détecter le signal faible, cartographier "
                   "les décideurs et préparer des entrées à forte valeur."),
        allow_delegation=False,
        verbose=True,
    )

    agent_chef_commercial = Agent(
        role="Responsable commercial",
        goal="Transformer les prospects chauds en clients via une campagne personnalisée multicanale",
        backstory=("Convertit l’intention en revenus grâce à des messages contextualisés "
                   "et un séquencement adapté au cycle de vente."),
        allow_delegation=False,
        verbose=True,
    )
    return agent_commercial, agent_chef_commercial
