import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns

df = pd.read_csv('d_4.csv')  # или любой другой путь

# 2. Преобразуем в матрицу (x и y -> индексы, ph -> значения)
heatmap_data = df.pivot(index='y', columns='x', values='ph')

# 3. Строим heatmap
plt.figure(figsize=(7, 6))
ax = sns.heatmap(heatmap_data, vmin=0, vmax=800, annot=False, cmap="viridis", cbar_kws={'label': 'Mean ph'})

# Инвертируем ось Y, чтобы (0,0) было внизу, а не вверху
ax.invert_yaxis()

# Подписи и отображение
plt.xlabel("x")
plt.ylabel("y")
plt.tight_layout()
plt.show()