from __future__ import annotations
from crewai import Task
from typing import List

def build_tasks(agent_commercial, agent_chef_commercial, tools_common: List, search_tool):
    profilage_prospect = Task(
        description=(
            "Analyse en profondeur {lead_name}, une entreprise du secteur {industry}. "
            "Objectifs :\n"
            "- Contexte & positionnement\n"
            "- Dirigeants & décideurs (fonction, LinkedIn si public)\n"
            "- Milestones/actualités : levée, produit, partenariats\n"
            "- Douleurs probables & besoins (avec hypothèses chiffrées si possible)\n"
            "- Pistes d'entrée / angles de valeur"
        ),
        expected_output=(
            "Un rapport Markdown structuré (titres, sous-titres, listes) prêt à partager "
            "avec le directeur commercial."
        ),
        tools=tools_common,
        agent=agent_commercial,
        output_file="outputs/prospect_report.md",
        async_execution=True
    )

    campagne_personnalisee = Task(
        description=(
            "À partir du rapport généré pour {lead_name}, rédige une campagne multicanale "
            "personnalisée à l’attention de {key_decision_maker} ({position}) en rebondissant "
            "sur leur {milestone}. Inclus :\n"
            "- 3 emails (intro, relance valeur, relance preuve)\n"
            "- 1 message LinkedIn (connexion)\n"
            "- 1 message LinkedIn (follow-up)\n"
            "- 3 objets d’email A/B testables\n"
            "Contraintes : ton bref, orienté ROI, preuve sociale, CTA clair; 120-150 mots/email."
        ),
        expected_output="Un fichier Markdown 'outputs/campaign_email.md' contenant la séquence.",
        tools=[t for t in [search_tool] if t],
        agent=agent_chef_commercial,
        context=[profilage_prospect],
        output_file="outputs/campaign_email.md"
    )

    return profilage_prospect, campagne_personnalisee
