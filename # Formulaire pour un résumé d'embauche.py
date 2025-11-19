"""
Formulaire pour un résumé d'embauche
 Auteur: Yann
Date: 2025-11-18
"""

#Collecte des informations de l'utilisateur
print("Bienvenue au formulaire d'embauche.")

# Obtenir réponse à ces quatre questions
while True:
    nom=input("Veuillez entrer votre nom complet : ")
    age=input("Veuillez entrer votre âge : ")
    experience=input("Veuillez décrire votre expérience professionnelle : ")
    competences=input("Veuillez lister vos compétences principales : ")
    # ce qui est dans la boucle doit etre indenté
    if nom == "" or experience == "" or competences == "" or age == "":
        print("Erreur: Tous les champs doivent être remplis.") #verification des champs vides
    else:
         print(age,experience,competences,nom )  #resumé des informations
         break

# Analyser les réponses
if int(age) < 15:
    print("Note: vous etes mineur, vous ne qualifiez pas pour cette emploi.") #verification de l'age
elif int(age) > 65:
    print("Note: Veuillez vérifier les conditions d'âge pour ce poste.") # conditions depandant de l'âge
else:
        print("Votre âge et vos autres réponses sont conformes aux exigences du poste.")

        print("Merci pour votre candidature,", nom+". Nous examinerons votre profil et vous contacterons bientôt.")#message de remerciement