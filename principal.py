import numpy as np
import random
from pyboy import PyBoy
from pyboy.utils import WindowEvent

class Ambiente:
    def __init__(self, nome_arquivo='mario.gb', modo_silencioso=True):
        tipo_janela = "headless" if modo_silencioso else "SDL2"
        self.pyboy = PyBoy(nome_arquivo, window=tipo_janela, debug=modo_silencioso)
        self.pyboy.set_emulation_speed(100)
        self.mario = self.pyboy.game_wrapper
        self.mario.start_game()

    def calcular_fitness(self):
        return self.mario.score + 30 * self.mario.level_progress + self.mario.time_left

    def fim_de_jogo(self):
        return self.mario.lives_left == 1 or self.mario.score < 0

    def reset(self):
        self.mario.reset_game()
        self.pyboy.tick()
        return self.get_estado()

    def passo(self, indice_acao, duracao):
        if self.fim_de_jogo():
            return None, 0, 0, "Fim de Jogo"
        
        acoes = {
            0: WindowEvent.PRESS_ARROW_LEFT,
            1: WindowEvent.PRESS_ARROW_RIGHT,
            2: WindowEvent.PRESS_BUTTON_A,
            3: (WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.PRESS_BUTTON_A)  # pular para a direita
        }
        acoes_liberacao = {
            0: WindowEvent.RELEASE_ARROW_LEFT,
            1: WindowEvent.RELEASE_ARROW_RIGHT,
            2: WindowEvent.RELEASE_BUTTON_A,
            3: (WindowEvent.RELEASE_ARROW_RIGHT, WindowEvent.RELEASE_BUTTON_A)
        }

        acao = acoes.get(indice_acao, WindowEvent.PASS)
        if isinstance(acao, tuple):
            for acao_parte in acao:
                self.pyboy.send_input(acao_parte)
        else:
            self.pyboy.send_input(acao)

        for _ in range(duracao):
            self.pyboy.tick()

        acao_liberacao = acoes_liberacao.get(indice_acao, WindowEvent.PASS)
        if isinstance(acao_liberacao, tuple):
            for acao_parte in acao_liberacao:
                self.pyboy.send_input(acao_parte)
        else:
            self.pyboy.send_input(acao_liberacao)
        
        self.pyboy.tick()

        tempo_restante = self.mario.time_left
        progresso_nivel = self.mario.level_progress
        return self.get_estado(), self.calcular_fitness(), tempo_restante, progresso_nivel

    def get_estado(self):
        return np.asarray(self.mario.game_area())

    def fechar(self):
        self.pyboy.stop()

class Individuo:
    def __init__(self):
        self.acoes = [(random.randint(0, 6), random.randint(5, 30)) for _ in range(1000)]
        self.fitness = 0

    def avaliar(self, ambiente):
        estado = ambiente.reset()
        fitness_total = 0
        tempo_maximo = 0
        movimentos_direita = 0
        jogo_terminou = False

        for acao, duracao in self.acoes:
            if jogo_terminou == "Fim de Jogo":
                break
            novo_estado, fitness, tempo_restante, jogo_terminou = ambiente.passo(acao, duracao)
            fitness_total += fitness
            tempo_maximo = max(tempo_maximo, tempo_restante)
            movimentos_direita += 1 if acao == 1 or acao == 3 else 0
            estado = novo_estado

        pontos_tempo = 500 if tempo_maximo > 0 else 0
        self.fitness = fitness_total + pontos_tempo + movimentos_direita * 10
        return self.fitness

def avaliar_fitness(individuo, ambiente):
    fitness = individuo.avaliar(ambiente)
    fitness_normalizado = fitness / 10000
    return fitness_normalizado

def iniciar_individuos(populacao):
    return [Individuo() for _ in range(populacao)]

def selecao(individuos):
    torneio_tamanho = 5
    selecionados = []
    for _ in range(len(individuos) // 2):
        competidores = random.sample(individuos, torneio_tamanho)
        vencedor = max(competidores, key=lambda ind: ind.fitness)
        selecionados.append(vencedor)
    return selecionados

def cruzamento(pai1, pai2):
    ponto_corte = random.randint(1, len(pai1.acoes) - 1)
    filho1 = Individuo()
    filho2 = Individuo()
    filho1.acoes = pai1.acoes[:ponto_corte] + pai2.acoes[ponto_corte:]
    filho2.acoes = pai2.acoes[:ponto_corte] + pai1.acoes[ponto_corte:]
    return filho1, filho2

def mutacao(individuo, taxa_mutacao=0.05):
    for i in range(len(individuo.acoes)):
        if random.random() < taxa_mutacao:
            acao, duracao = individuo.acoes[i]
            novo_acao = (acao + random.choice([-1, 1])) % 4
            novo_duracao = max(1, min(5, duracao + random.choice([-1, 1])))
            individuo.acoes[i] = (novo_acao, novo_duracao)

def imprimir_acoes_individuo(individuo):
    nomes_acoes = ["esquerda", "direita", "A", "direita + A"]
    acoes = [f"{nomes_acoes[acao]} por {duracao} ticks" for acao, duracao in individuo.acoes]
    return acoes

def aumentar_tamanho_acoes(populacao, incremento):
    for individuo in populacao:
        individuo.acoes.extend([(random.randint(0, 3), random.randint(1, 5)) for _ in range(incremento)])

def algoritmo_genetico(populacao, ambiente, geracoes=100):
    melhor_individuo = None
    melhor_fitness = -np.inf

    for geracao in range(geracoes):
        if geracao % 10 == 0:
            aumentar_tamanho_acoes(populacao, 500)  # Aumenta 500 ações a cada 10 gerações

        for individuo in populacao:
            individuo.fitness = avaliar_fitness(individuo, ambiente)
            print(f"Fitness: {individuo.fitness}")

        selecionadas = selecao(populacao)
        descendentes = []
        while len(descendentes) < len(populacao) - len(selecionadas):
            pai1, pai2 = random.sample(selecionadas, 2)
            filho1, filho2 = cruzamento(pai1, pai2)
            descendentes.extend([filho1, filho2])

        for filho in descendentes:
            mutacao(filho)

        populacao = selecionadas + descendentes[:len(populacao) - len(selecionadas)]

        fitness_atual = max(individuo.fitness for individuo in populacao)
        individuo_atual = max(populacao, key=lambda n: n.fitness)
        if fitness_atual > melhor_fitness:
            melhor_fitness = fitness_atual
            melhor_individuo = individuo_atual

        print(f"Geração {geracao}: Melhor Fitness {melhor_fitness}")
        print(f"Melhores Ações: {imprimir_acoes_individuo(melhor_individuo)}")

    return melhor_individuo

def rodar_melhor_modelo(ambiente, melhor_individuo):
    while True:
        estado = ambiente.reset()
        for acao in melhor_individuo.acoes:
            estado, fitness, tempo_restante, progresso_nivel = ambiente.passo(acao[0], acao[1])
        print("Loop completado, reiniciando...")

if __name__ == "__main__":
    ambiente = Ambiente(modo_silencioso=False)
    populacao = iniciar_individuos(20)
    melhor_individuo = algoritmo_genetico(populacao, ambiente)
    rodar_melhor_modelo(ambiente, melhor_individuo)
    ambiente.fechar()
