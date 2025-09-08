import numpy as np
from skimage import io
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# 1. Load image
image = io.imread("file:///C:/Users/Microsoft/Downloads/istockphoto-2173440246-1024x1024.jpg")

# 2. Reshape to (num_pixels, 3) for RGB
pixels = image.reshape(-1, 3)

# 3. Cluster colors (let’s use 3 main colors)
kmeans = KMeans(n_clusters=3, random_state=42)
kmeans.fit(pixels)

# 4. Find the largest cluster (most frequent color)
unique, counts = np.unique(kmeans.labels_, return_counts=True)
dominant_color = kmeans.cluster_centers_[unique[np.argmax(counts)]]

print("Dominant Color (RGB):", dominant_color.astype(int))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
ax1.imshow(image)
ax1.set_title("Original Image")
ax1.axis("off")
# 5. Show the dominant color
ax2.imshow([[dominant_color.astype(int)/255]])  # scale to 0-1 for matplotlib
ax2.set_title("Dominant Color")
ax2.axis("off")
plt.show()
