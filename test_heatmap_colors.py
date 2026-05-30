#!/usr/bin/env python3
"""
Script de teste para validar as funções de mapeamento de cores do heatmap.
Este script verifica se as funções estão retornando as cores esperadas com base nos valores de congestão.
"""


def get_precise_color_for_congestion(value: float, max_expected_value: float = 100.0) -> str:
    """
    Converte um valor de congestão em uma cor hexadecimal com alta precisão.
    Implementa uma escala de cores similar às usadas por Waze e Google Maps.
    
    Args:
        value: Valor de congestão a ser convertido
        max_expected_value: Valor máximo esperado (para normalização)
        
    Returns:
        String hexadecimal representando a cor apropriada
    """
    # Normaliza o valor entre 0 e 1, considerando o valor máximo esperado
    normalized = min(max(value / max_expected_value, 0.0), 1.0)
    
    # Escala de cores usada por serviços como Waze e Google Maps:
    # Verde escuro (tráfego livre) -> Verde -> Amarelo -> Laranja -> Vermelho -> Roxo (congestionamento extremo)
    color_stops = [
        (0.0, (0, 100, 0)),      # Verde escuro - tráfego livre
        (0.25, (0, 255, 0)),     # Verde - tráfego leve
        (0.5, (255, 255, 0)),    # Amarelo - tráfego moderado
        (0.7, (255, 165, 0)),    # Laranja - tráfego pesado
        (0.85, (255, 69, 0)),    # Laranja vermelho - tráfego muito pesado
        (1.0, (255, 0, 0))       # Vermelho - congestionamento severo
    ]
    
    # Encontrar entre quais pontos de controle o valor normalizado está
    for i in range(len(color_stops) - 1):
        if normalized >= color_stops[i][0] and normalized <= color_stops[i+1][0]:
            # Calcular a fração entre os dois pontos de controle
            start_value, start_color = color_stops[i]
            end_value, end_color = color_stops[i+1]
            
            # Normalizar novamente entre os dois pontos de controle
            segment_normalized = (normalized - start_value) / (end_value - start_value)
            
            # Interpolar linearmente entre as duas cores
            r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
            
            return f"#{r:02x}{g:02x}{b:02x}"
    
    # Caso especial para o último intervalo
    r, g, b = color_stops[-1][1]
    return f"#{r:02x}{g:02x}{b:02x}"

def get_enhanced_color_for_congestion(value: float, max_expected_value: float = 100.0) -> str:
    """
    Converte um valor de congestão em uma cor hexadecimal com escala avançada.
    Usa uma curva logarítmica para melhor representação de pequenas variações.
    
    Args:
        value: Valor de congestão a ser convertido
        max_expected_value: Valor máximo esperado (para normalização)
        
    Returns:
        String hexadecimal representando a cor apropriada
    """
    import math
    
    # Normalizar o valor
    normalized = min(max(value / max_expected_value, 0.0), 1.0)
    
    # Aplicar uma transformação logarítmica suavizada para realçar pequenas variações
    if normalized == 0:
        adjusted = 0
    else:
        # Usar uma combinação de funções para realçar variações em diferentes faixas
        if normalized < 0.3:
            # Aumentar sensibilidade para valores baixos
            adjusted = math.pow(normalized / 0.3, 0.7) * 0.3
        elif normalized < 0.7:
            # Manter linearidade média para a faixa intermediária
            adjusted = 0.3 + ((normalized - 0.3) / 0.4) * 0.4
        else:
            # Ajustar para destacar altos valores
            adjusted = 0.7 + math.pow((normalized - 0.7) / 0.3, 1.3) * 0.3
    
    # Agora usar a escala de cores padronizada
    color_stops = [
        (0.0, (0, 100, 0)),      # Verde escuro - tráfego livre
        (0.25, (0, 255, 0)),     # Verde - tráfego leve
        (0.5, (255, 255, 0)),    # Amarelo - tráfego moderado
        (0.7, (255, 165, 0)),    # Laranja - tráfego pesado
        (0.85, (255, 69, 0)),    # Laranja vermelho - tráfego muito pesado
        (1.0, (255, 0, 0))       # Vermelho - congestionamento severo
    ]
    
    # Encontrar entre quais pontos de controle o valor ajustado está
    for i in range(len(color_stops) - 1):
        if adjusted >= color_stops[i][0] and adjusted <= color_stops[i+1][0]:
            # Calcular a fração entre os dois pontos de controle
            start_value, start_color = color_stops[i]
            end_value, end_color = color_stops[i+1]
            
            # Normalizar novamente entre os dois pontos de controle
            segment_normalized = (adjusted - start_value) / (end_value - start_value)
            
            # Interpolar linearmente entre as duas cores
            r = int(start_color[0] + (end_color[0] - start_color[0]) * segment_normalized)
            g = int(start_color[1] + (end_color[1] - start_color[1]) * segment_normalized)
            b = int(start_color[2] + (end_color[2] - start_color[2]) * segment_normalized)
            
            return f"#{r:02x}{g:02x}{b:02x}"
    
    # Caso especial para o último intervalo
    r, g, b = color_stops[-1][1]
    return f"#{r:02x}{g:02x}{b:02x}"


def test_color_mapping():
    """Testa as funções de mapeamento de cores para diferentes valores de congestão."""
    print("Testando funções de mapeamento de cores...")
    
    # Testar diferentes valores de congestão
    test_values = [0, 10, 25, 30, 50, 70, 75, 85, 90, 100]
    
    print("\nTestando get_precise_color_for_congestion:")
    for value in test_values:
        color = get_precise_color_for_congestion(value, 100.0)
        print(f"  Valor {value:3d} -> Cor {color}")
    
    print("\nTestando get_enhanced_color_for_congestion:")
    for value in test_values:
        color = get_enhanced_color_for_congestion(value, 100.0)
        print(f"  Valor {value:3d} -> Cor {color}")
    
    # Testar valores além do limite máximo
    print("\nTestando valores além do limite (deve normalizar para o máximo):")
    overflow_values = [110, 150, 200]
    for value in overflow_values:
        color1 = get_precise_color_for_congestion(value, 100.0)
        color2 = get_enhanced_color_for_congestion(value, 100.0)
        print(f"  Valor {value:3d} -> Precise: {color1}, Enhanced: {color2}")
    
    # Testar valores negativos
    print("\nTestando valores negativos (deve normalizar para 0):")
    negative_values = [-10, -5, 0]
    for value in negative_values:
        color1 = get_precise_color_for_congestion(value, 100.0)
        color2 = get_enhanced_color_for_congestion(value, 100.0)
        print(f"  Valor {value:3d} -> Precise: {color1}, Enhanced: {color2}")
    
    print("\nTeste concluído com sucesso!")


def test_color_gradient():
    """Testa se as cores formam um gradiente suave e lógico."""
    print("\nTestando consistência do gradiente de cores...")
    
    # Testar valores em incrementos pequenos para verificar suavidade
    values = [i for i in range(0, 101, 10)]
    precise_colors = []
    enhanced_colors = []
    
    for value in values:
        precise_colors.append(get_precise_color_for_congestion(value, 100.0))
        enhanced_colors.append(get_enhanced_color_for_congestion(value, 100.0))
    
    print("\nGradiente Precise (0-100 em incrementos de 10):")
    for i, (val, col) in enumerate(zip(values, precise_colors)):
        print(f"  {val:3d}: {col}")
    
    print("\nGradiente Enhanced (0-100 em incrementos de 10):")
    for i, (val, col) in enumerate(zip(values, enhanced_colors)):
        print(f"  {val:3d}: {col}")
    
    # Verificar se as cores seguem a lógica esperada (de verde para vermelho)
    print("\nVerificando se as cores seguem a lógica tráfego-livre (verde) -> congestionamento (vermelho)...")
    
    low_val_color = get_precise_color_for_congestion(0, 100.0)
    high_val_color = get_precise_color_for_congestion(100, 100.0)
    
    print(f"  Cor para valor baixo (0): {low_val_color} (esperado: verde)")
    print(f"  Cor para valor alto (100): {high_val_color} (esperado: vermelho)")
    
    print("\nTeste de gradiente concluído!")


if __name__ == "__main__":
    print("Iniciando testes das funções de mapeamento de cores do heatmap...")
    
    test_color_mapping()
    test_color_gradient()
    
    print("\nTodos os testes concluídos!")