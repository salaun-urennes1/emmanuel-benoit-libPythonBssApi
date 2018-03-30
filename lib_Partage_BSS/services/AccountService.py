# -*-coding:utf-8 -*
"""
Module contenant les méthodes permettant d'appeler les services de l'API BSS concernant les comptes
"""
import re
from collections import OrderedDict
from time import time

from lib_Partage_BSS import models, utils, services
from lib_Partage_BSS.exceptions import NameException, DomainException, ServiceException
from .GlobalService import callMethod


def fillAccount(accountResponse):
    """
    Permet de remplir un objet compte depuis une réponse de l'API BSS

    :param accountResponse: l'objet account renvoyé par l'API
    :return: l'objet account créé
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail valide
    """
    if not utils.checkIsMailAddress(accountResponse["name"]):
        raise NameException("L'adresse mail " + accountResponse["name"] + " n'est pas valide")

    retAccount = models.Account(accountResponse["name"])
    accountKeys = accountResponse.keys()
    for attr in accountKeys:
        if accountResponse[attr] is not None:
            if isinstance(accountResponse[attr], str):
                if accountResponse[attr] == "TRUE" or accountResponse[attr] == "FALSE":
                    retAccount.__setattr__("_" + attr, utils.changeStringToBoolean(accountResponse[attr]))
                else:
                    retAccount.__setattr__("_" + attr, accountResponse[attr])
            elif isinstance(accountResponse[attr], OrderedDict):
                if "type" in accountResponse[attr].keys():
                    if accountResponse[attr]["type"] == "integer":
                        retAccount.__setattr__("_" + attr, int(accountResponse[attr]["content"]))
                    elif accountResponse[attr]["type"] == "array":
                        if attr == "zimbraZimletAvailableZimlets":
                            retAccount.__setattr__("_" + attr, accountResponse[attr]["zimbraZimletAvailableZimlet"])
                        elif attr == "zimbraMailAlias":
                            retAccount.__setattr__("_" + attr, accountResponse[attr]["zimbraMailAlias"])
    return retAccount


def getAccount(name):
    """
    Méthode permettant de récupérer les informations d'un compte via l'API BSS

    :return: Le compte récupéré ou None si le compte n'existe pas
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail valide
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    data = {
        "name": name
    }
    response = callMethod(services.extractDomain(name), "GetAccount", data)
    if utils.checkResponseStatus(response["status"]):
        account = response["account"]
        return fillAccount(account)
    elif re.search(".*no such account.*", response["message"]):
        return None
    else:
        raise ServiceException(response["status"], response["message"])




def getAllAccounts(domain, limit=100, offset=0, ldapQuery=""):
    """
    Permet de rechercher tous les comptes mail d'un domain

    :param domain: le domaine de la recherche
    :param limit: le nombre de résultats renvoyés (optionnel)
    :param offset: le nombre à partir duquel les comptes sont renvoyés (optionnel)
    :param ldapQuery: un filtre ldap pour affiner la rechercher (optionnel)
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises DomainException: Exception levée si le domaine n'est pas un domaine valide
    """
    if not utils.checkIsDomain(domain):
        raise DomainException
    data = {
        "limit": limit,
        "offset": offset,
        "ldap_query": ldapQuery
    }
    response = callMethod(domain, "GetAllAccounts", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])
    if len(response["accounts"]) == 1:
        return []
    else:
        accounts = response["accounts"]["account"]
        retAccounts = []
        if isinstance(accounts, list):
            for account in accounts:
                retAccounts.append(fillAccount(account))
        else:
            retAccounts.append(fillAccount(accounts))
        return retAccounts



def createAccount(name,userPassword, cosId, account = None):
    """
    Méthode permettant de créer un compte via l'API BSS en lui passant en paramètre l'empreinte du mot de passe (SSHA) et le cosId

    :param userPassword: l'empreine du mot de passe de l'utilisateur
    :param cosId: l'identifiant du cosId à appliquer pour le compte
    :param account: objet account contenant les informations à ajouter dans le compte (optionnel)
    :return: Le compte créé
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail valide
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """

    if not re.search(r'^\{\S+\}', userPassword):
        raise NameException("Le format de l'empreinte du mot de passe n'est pas correcte ; format attendu : {algo}empreinte")

    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")

    data = {
            "name": name,
            "password": "",
            "userPassword": userPassword,
            "zimbraHideInGal": "FALSE",
            "zimbraCOSId": cosId
        }
    response = callMethod(services.extractDomain(name), "CreateAccount", data)

    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])

    if account is not None:
        modifyAccount(account)

    return getAccount(name)


def deleteAccount(name):
    """
    Permet de supprimer un compte

    :param name: Nom du compte à supprimer
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail valide
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    data = {
        "name": name
    }
    response = callMethod(services.extractDomain(name), "DeleteAccount", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])




def preDeleteAccount(name):
    """
    Permet de mettre un compte dans un état de préSuppression
    Cette méthode désactive le compte puis le renomme (ajout d'un préfixe 'deleted_timestampactuel_name')

    :param name: nom du compte à préSupprimer
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail valide
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    closeAccount(name)
    newname = "readytodelete_"+utils.changeTimestampToDate(round(time()))+"_"+name
    renameAccount(name, newname)
    return newname




def restorePreDeleteAccount(name):
    """
    Permet d'annuler la préSuppression d'un compte

    :param name: le nom du compte preSupprimé à restaurer
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsPreDeleteAccount(name):
        raise NameException("L'adresse mail " + name + " n'est pas une adresse mail preSupprimé")
    activateAccount(name)
    renameAccount(name, name.split("_")[2])



def modifyAccount(account):
    """
    Permet de modifier un compte via l'API

    :param account: un objets compte avec les attributs à changer
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(account.name):
        raise NameException("L'adresse mail " + account.name + " n'est pas valide")
    data = {}
    for attr in account.__dict__:
        if attr != "_zimbraZimletAvailableZimlets":
            if account.__getattribute__(attr) is not None:
                attrValue = account.__getattribute__(attr)
                if isinstance(attrValue, bool):
                    attrValue = utils.changeBooleanToString(attrValue)
                data[attr[1:]] = attrValue
    response = callMethod(services.extractDomain(account.name), "ModifyAccount", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])


def setPassword(name, newPassword):
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    data={
        "name": name,
        "password": newPassword
    }
    response = callMethod(services.extractDomain(name), "SetPassword", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])

def modifyPassword(name, newUserPassword):
    """
    Pour modifier le mot de passe on n'accepte que l'empreinte du mot de passe.
    On commence par faire un SetPassword avec une valeur factice pour forcer la déconnexion des sessions en cours
    On passe ensuite via ModifyAccount l'empreinte du nouveau mot de passe

    :param newUserPassword:
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    setPassword(name,"valeurPourDeconnecterLesSessions")
    data = {
        "name": name,
        "userPassword": newUserPassword
    }
    response = callMethod(services.extractDomain(name), "ModifyAccount", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])



def addAccountAlias(name, newAlias):
    """
    Méthode permettant d'ajouter un alias d'un compte

    :param name: le nom du compte
    :param aliasToDelete: l'alias a ajouter
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name) or not utils.checkIsMailAddress(newAlias):
        raise NameException("L'adresse mail " + name + " ou " + newAlias + " n'est pas valide")
    data = {
        "name": name,
        "alias": newAlias
    }
    response = callMethod(services.extractDomain(name), "AddAccountAlias", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])




def removeAccountAlias(name, aliasToDelete):
    """
    Méthode permettant de supprimer un alias d'un compte

    :param name: le nom du compte
    :param aliasToDelete: l'alias a supprimer
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name) or not utils.checkIsMailAddress(aliasToDelete):
        raise NameException("L'adresse mail " + name +" ou "+aliasToDelete+" n'est pas valide")
    data = {
        "name": name,
        "alias": aliasToDelete
    }
    response = callMethod(services.extractDomain(name), "RemoveAccountAlias", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])



def modifyAccountAliases(name, listOfAliases):
    """
    Méthode permettant de changer l'ensemble des alias d'un compte par ceux passés en paramètre

    :param name: le nom du compte
    :param listOfAliases: la liste des alias pour le compte
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    :raises TypeError: Exception levée si le parametre listOfAliases n'est pas une liste
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    if not isinstance(listOfAliases, list):
        raise TypeError
    account = getAccount(name)
    #On vérifie que les adresses mail passées en paramètres sont des adresses valide
    for alias in listOfAliases:
        if not utils.checkIsMailAddress(alias):
            raise NameException("L'adresse mail " + alias + " n'est pas valide")
    #On parcour la liste passé en paramètre
    for alias in listOfAliases:
        if isinstance(account.zimbraMailAlias, list) or isinstance(account.zimbraMailAlias, str):
            #si la l'adresse mail n'est pas présente dans partage on la rajoute
            if alias not in account.zimbraMailAlias:
                addAccountAlias(name, alias)
        #si la liste partage est vide on rajoute l'adresse
        elif account.zimbraMailAlias is None:
            addAccountAlias(name, alias)
    if isinstance(account.zimbraMailAlias, list):
        #On parcours la liste des adresses partages
        for alias in account.zimbraMailAlias:
            #Si l'adresse n'est pas présente dans la liste passé en parametre on supprime l'adresse de partage
            if alias not in listOfAliases:
                removeAccountAlias(name, alias)
    #Si le compte n'a qu'un alias on test si il est présent ou pas dans la liste passé en paramètre
    elif isinstance(account.zimbraMailAlias, str):
        if account.zimbraMailAlias not in listOfAliases:
            removeAccountAlias(name, account.zimbraMailAlias)


def activateAccount(name):
    """
    Méthode permettant de passer l'état d'un compte à activer

    :param name: le nom du compte à (ré)activer
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    account = models.Account(name)
    account.zimbraAccountStatus = "active"
    modifyAccount(account)


def lockAccount(name):
    """
    Méthode permettant de passer l'état d'un compte à lock
    Cette état déconnecte toutes les instances du compte et empêche la connexion à celui-ci.
    Le compte sera toujours visible dans la GAL et les mails seront toujours acheminés vers cette boîte

    :param name: le nom du compte à verrouiller
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail " + name + " n'est pas valide")
    setPassword(name, "valeurPourDeconnecterLesSessions")
    account = models.Account(name)
    account.zimbraAccountStatus = "locked"
    modifyAccount(account)


def closeAccount(name):
    """
    Cette méthode déconnecte toutes les instances du compte et empêche la connexion à celui-ci.
    Le compte ne sera plus visible dans la GAL et les mails entrants seront rejetés

    :param name: le nom du compte à Désactiver
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name):
        raise NameException("L'adresse mail n'est pas valide")
    setPassword(name, "valeurPourDeconnecterLesSessions")
    account = models.Account(name)
    account.zimbraAccountStatus = "closed"
    account.zimbraHideInGal = True
    modifyAccount(account)


def renameAccount(name, newName):
    """
    Permet de renommer un compte :param name: nom du compte à renommer :param newName: le nouveau nom du compte

    :param name: le nom du compte à renommer
    :param newName: le nouveau nom du compte
    :raises ServiceException: Exception levée si la requête vers l'API à echoué. L'exception contient le code de l'erreur et le message
    :raises NameException: Exception levée si le nom n'est pas une adresse mail preSupprimé
    :raises DomainException: Exception levée si le domaine de l'adresse mail n'est pas un domaine valide
    """
    if not utils.checkIsMailAddress(name) or not utils.checkIsMailAddress(newName):
        raise NameException("L'adresse mail n'est pas valide")
    data = {
        "name": name,
        "newname": newName
    }
    response = callMethod(services.extractDomain(name), "RenameAccount", data)
    if not utils.checkResponseStatus(response["status"]):
        raise ServiceException(response["status"], response["message"])
