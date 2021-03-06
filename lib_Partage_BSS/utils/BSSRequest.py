# -*-coding:utf-8 -*
"""
Module permettant de faire des requêtes HTTP vers l'API BSS et de parser la réponse
"""
import xml.etree.ElementTree as et
from xmljson import yahoo as ya
import requests

from lib_Partage_BSS.exceptions import ServiceException


def parseResponse(stringXml):
    """
    Méthode permettant de transformer la reponse XML de l'API BSS en objet Python

    :param stringXml: la chaine XML à transformer en objet python
    :return: l'objet response obtenu
    """
    response = ya.data(et.fromstring(stringXml))
    if "Response" in response:
        return response["Response"]
    elif "response" in response:
        return response["response"]
    else:
        raise ServiceException(3,"Problème format réponse")


def postBSS(url, data):
    """
    Permet de récupérer la réponse d'une requête auprès de l'API BSS

    :param url: url de l'action demandée avec si nécessaire le token
    :param data: le body de la requête post
    :return: BSSResponse la réponse de l'API BSS
    """
    return parseResponse(requests.post(url, data).text)