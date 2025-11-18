# Formulaire pour un résumé d'embauche
    #Collecte des informations de l'utilisateur
print("Bienvenue au formulaire d'embauche.")
nom=input("Veuillez entrer votre nom complet : ")
age=input("Veuillez entrer votre âge : ")
experience=input("Veuillez décrire votre expérience professionnelle : ")
competences=input("Veuillez lister vos compétences principales : ")
print(age,experience,competences,nom )  #resumé des informations
while True:
if nom =="" or experience =="" or competences =="" or age =="":
    print("Erreur: Tous les champs doivent être remplis.") #verification des champs vides
    while True:
if int(age) < 15:
    print("Note: vous etes mineur, vous ne qualifiez pas pour cette emploi.") #verification de l'age
elif int(age) > 65:
    print("Note: Veuillez vérifier les conditions d'âge pour ce poste.") # conditions depandant de l'âge
else:
        print("Votre âge et vos autres réponses sont conformes aux exigences du poste.")
       
else:
print("merci pour votre candidature,", nom+". Nous examinerons votre profil et vous contacterons bientôt.")#message de remerciement