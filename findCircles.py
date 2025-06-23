import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from miniball import Miniball  # pip install miniball

def kmeans_with_minimum_circles(points, n_clusters=3):
    """
    Agrupa puntos usando k-means y encuentra el círculo mínimo para cada cluster.
    
    Args:
        points: Array numpy de forma (n, 2) con las coordenadas x, y
        n_clusters: Número de clusters a crear
    
    Returns:
        clusters: Lista de arrays con los puntos de cada cluster
        centers: Lista de centros de círculos [(x1, y1), (x2, y2), ...]
        radii: Lista de radios [r1, r2, ...]
    """
    # Aplicar k-means
    kmeans = KMeans(n_clusters=n_clusters, random_state=0)
    labels = kmeans.fit_predict(points)
    
    clusters = []
    centers = []
    radii = []
    
    # Para cada cluster, encontrar el círculo mínimo
    for i in range(n_clusters):
        # Obtener puntos de este cluster
        cluster_points = points[labels == i]
        
        # Si no hay suficientes puntos, saltamos
        if len(cluster_points) < 3:
            if len(cluster_points) > 0:
                # Para 1 o 2 puntos, calculamos un círculo simple
                center = np.mean(cluster_points, axis=0)
                if len(cluster_points) == 1:
                    radius = 0.1  # Radio pequeño para un solo punto
                else:
                    radius = np.max(np.linalg.norm(cluster_points - center, axis=1))
                
                clusters.append(cluster_points)
                centers.append(center)
                radii.append(radius)
            continue
        
        # Usar miniball para encontrar el círculo mínimo
        mb = Miniball(cluster_points)
        center = mb.center()
        radius = np.sqrt(mb.squared_radius())
        
        clusters.append(cluster_points)
        centers.append(center)
        radii.append(radius)
    
    return clusters, centers, radii

def plot_kmeans_circles(points, clusters, centers, radii):
    """
    Visualiza los clusters y sus círculos mínimos.
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Colores para diferentes clusters
    colors = ['blue', 'green', 'red', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
    
    # Plotear todos los puntos originales como referencia (más pequeños)
    ax.scatter(points[:, 0], points[:, 1], color='blue', alpha=0.5, s=20)
    
    # Plotear cada cluster y su círculo
    for i, (cluster, center, radius) in enumerate(zip(clusters, centers, radii)):
        color = colors[i % len(colors)]
        
        # Plotear puntos del cluster
        ax.scatter(cluster[:, 0], cluster[:, 1], color=color, s=50, label=f'Cluster {i+1}')
        
        # Plotear centro del círculo
        ax.scatter(center[0], center[1], color='black', marker='x', s=100)
        
        # Plotear círculo mínimo
        circle = patches.Circle(center, radius, fill=False, edgecolor=color, linewidth=2)
        ax.add_patch(circle)
    
    ax.set_aspect('equal')
    ax.legend()
    ax.set_title('K-means con Círculos Mínimos')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# Ejemplo de uso
if __name__ == "__main__":
    # Generar datos de ejemplo (3 clusters)
    np.random.seed(42)
    
    # Cluster 1
    cluster1 = np.random.randn(80, 2) * 5 + np.array([20, 20])
    
    # Cluster 2
    cluster2 = np.random.randn(60, 2) * 3 + np.array([50, 50])
    
    # Cluster 3
    cluster3 = np.random.randn(40, 2) * 4 + np.array([80, 30])
    
    # Combinar todos los puntos
    all_points = np.vstack([cluster1, cluster2, cluster3])
    
    # Aplicar k-means con círculos mínimos
    clusters, centers, radii = kmeans_with_minimum_circles(all_points, n_clusters=3)
    
    # Visualizar resultados
    plot_kmeans_circles(all_points, clusters, centers, radii)
    
    # Imprimir información de los círculos
    #for i, (center, radius) in enumerate(zip(centers, radii)):
        #print(f"Círculo {i+1}: Centro = {center}, Radio = {radius:.2f}")