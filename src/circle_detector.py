# circle_detector.py
import numpy as np
from sklearn.cluster import DBSCAN
import miniball

class CircleDetector:
    def __init__(self, eps=10, min_samples=5):
        """
        Args: 
            eps: Maximum distance to consider that two points are in the same cluster 
            min_samples: Minimum number of points to form a cluster
        """
        self.eps = eps
        self.min_samples = min_samples
    
    def group_points_into_circles(self, points):
        """
        Group points into circles using DBSCAN for clustering and Miniball to find the minimum circle that contains each group.
        Args:
            points: List of tuples (x, y) with the coordinates of the points
            Returns:circles: List of tuples (x, y, radius) that represent the circles.
        """
        
        # Validate that all points are tuples/lists of 2 elements
        valid_points = [p for p in points if isinstance(p, (list, tuple)) and len(p) == 2]
        
        # Check if there are valid points
        if not valid_points:
            return []
        
        # Convert list of points to numpy array
        points_array = np.array(valid_points)
        
        # If there are not enough points, return empty circles.
        if len(points_array) < self.min_samples:
            if len(points_array) > 0:
                # If there are few points, create a single circle that contains them all.
                center, squared_radius = miniball.get_bounding_ball(cluster_points)
                radius = np.sqrt(squared_radius)
                return [(center[0], center[1], radius)]
            return []
        
        # Apply DBSCAN to group the points
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(points_array)
        labels = clustering.labels_
        
        # Find minimum circles for each cluster
        circles = []
        unique_labels = set(labels)
        
        for label in unique_labels:
            # Ignore the noise (label -1)
            if label == -1:
                continue
                
            # Get points from this cluster
            cluster_points = points_array[labels == label]
            
            # Calculate the minimum circle for this cluster

            try:
                center, squared_radius = miniball.get_bounding_ball(cluster_points)
                radius = np.sqrt(squared_radius)

                # Add a little margin to the radius (5%)
                radius *= 1.05
                circles.append((center[0], center[1], radius))

            except Exception as e:
                print(f"Error al calcular el circulo: {e}")

            #If it fails, create a small generic circle around the average point.

                if len(cluster_points) > 0:
                    mean_point = np.mean(cluster_points, axis = 0)
                    circles.append((mean_point[0],mean_point[1],5))

        return circles
    
    def merge_overlapping_circles(self, circles, overlap_threshold=0.7):
        """
        Merge circles that significantly overlap.

        Args:
            circles: List of tuples (x, y, radius)  
            overlap_threshold: Overlap threshold for merging circles
            
        Returns:
            merged_circles: List of merged circles
        """
        if not circles:
            return []
            
        # Sort circles by radius (from largest to smallest)
        sorted_circles = sorted(circles, key=lambda x: x[2], reverse=True)
        merged_circles = []
        
        while sorted_circles:
            # Take the largest circle
            current = sorted_circles.pop(0)
            merged_circles.append(current)
            
            # Filter circles that do not significantly overlap with the current one.
            remaining_circles = []
            for circle in sorted_circles:
                # Calculate distance between centers
                distance = np.sqrt((circle[0] - current[0])**2 + (circle[1] - current[1])**2)
                
                # If the distance is greater than the sum of the radii, there is no overlap.
                if distance > current[2] + circle[2]:
                    remaining_circles.append(circle)
                    continue
                    
                # Calculate overlap
                overlap_ratio = min(circle[2], current[2]) / max(circle[2], current[2])
                
                # If the overlap is less than the threshold, keep the circle.
                if overlap_ratio < overlap_threshold:
                    remaining_circles.append(circle)
            
            sorted_circles = remaining_circles
            
        return merged_circles