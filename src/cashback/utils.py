def digito_mod11(digitos):
    # https://pt.wikipedia.org/wiki/D%C3%ADgito_verificador#M%C3%B3dulo_11
    algarismos = digitos[::-1]
    digito = 0
    for i in range(len(algarismos)):
        digito += algarismos[i] * (9 - (i % 10))
    digito = digito % 11 % 10
    return digito
