import numpy as np
import time
import distance_calc as distc

def initialize_centroids(points, k):
    """
    Randomly initialize centroids of data points.
    Args:
        points: array of shape (N, X)
                    N = number of samples,
                    X = dimension of latent space - number of features
        k: int - number of clusters
    """
    indexes = np.random.randint(points.shape[0], size=k)
    return points[indexes]

def find_distance_matrix_quantum(points, centroid, device_name):
    """ 
    Modified version of scipy.spatial.distance.cdist() function.
    Args:
        points: array of shape (N, X)
                    N = number of samples,
                    X = dimension of latent space - number of features
        centroid: array of shape (1, X)
    """
    
    points = np.asarray(points)
    centroid = np.asarray(centroid)

    n_features = points.shape[1]
    n_events = points.shape[0]
    
    if points.shape[1] != centroid.shape[1]:
        raise ValueError('Points and centroid need to have same number of features.')

    dist_matrix = np.zeros((n_events, centroid.shape[0]))
    for i in range(n_events):
        distance, _ = distc.DistCalc_DI(points[i,:], centroid[0], device_name)
        dist_matrix[i,:] = distance
    return dist_matrix

def geometric_median(points, eps=1e-6, device_name='/GPU:0'):
    """
    Implementation from Reference - DOI: 10.1007/s00180-011-0262-4 for "VaZh" algorithm
    Args:
        points: array of shape (N, X)
                    N = number of samples,
                    X = dimension of latent space - number of features
    """
    
    if points.size==0: 
        print("For this class there is no points assigned!")
        return
    
    median = np.mean(points, 0) # starting median

    while True:
        D = find_distance_matrix_quantum(points, [median], device_name)
        nonzeros = (D != 0)[:, 0]
        Dinv = 1 / D[nonzeros]
        Dinv_sum = np.sum(Dinv)
        W = Dinv / Dinv_sum
        T1 = np.sum(W * points[nonzeros], 0) #scaled sum of all points - Eq. (7) in Ref.
        
        num_zeros = len(points) - np.sum(nonzeros) # number of points = y
        if num_zeros == 0: #then next median is scaled sum of all points
            new_median = T1
        elif num_zeros == len(points):
            return median
        else:
            R = (T1 - median) * Dinv_sum # Eq. (9)
            r = np.linalg.norm(R)
            gamma = 0 if r == 0 else num_zeros/r
            gamma = min(1, gamma) # Eq. (10)
            new_median = (1-gamma)*T1 + gamma*median # Eq. (11)
        
        # converge condition    
        dist_med_newmed,_ = distc.DistCalc_DI(median, new_median, device_name=device_name)
        if dist_med_newmed < eps:
            return new_median
        median = new_median # next median
        
        
def find_centroids_GM(points, cluster_labels, clusters=2):
    """
    Args:
        points: array of shape (N, X)
                    N = number of samples,
                    X = dimension of latent space - number of features
        cluster_labels: array of shape (N,) - cluster labels assigned to each data point
        clusters: int - number of clusters
    """    
    centroids = np.zeros([clusters, points.shape[1]])
    k = points.shape[1]
    for j in range(clusters):
        print(f'Searching centroids for cluster {j}')
        points_class_i = points[cluster_labels==j]
        median = geometric_median(points_class_i)
        centroids[j,:] = median
        print(f'Found for cluster {j}')
    return np.array(centroids)

def find_nearest_neighbour_DI(points, centroids, device_name='/GPU:0'):
    """
    Args:
        points: array of shape (N, X)
                    N = number of samples,
                    X = dimension of latent space;
        centroids: array of shape (N, X)
    Returns:
        cluster labels: array of shape (N,) specifying to which cluster each point is assigned
        distances: array of shape (N,) specifying distances to nearest cluster for each point
    """
    
    n = points.shape[0]
    num_features = points.shape[1]
    k = centroids.shape[0] # number of centroids
    cluster_label=[]
    distances=[]
    
    for i in range(n): # through all training samples
        dist=[]
        for j in range(k): # distance of each training example to each centroid
            temp_dist, _ = distc.DistCalc_DI(points[i,:], centroids[j,:], device_name=device_name, shots_n=10000) # returning back one number for all latent dimensions!
            dist.append(temp_dist)
        cluster_index = np.argmin(dist) # classical minimization
        cluster_label.append(cluster_index)
        distances.append(dist)
    return np.asarray(cluster_label), np.asarray(distances)
