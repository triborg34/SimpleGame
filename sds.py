import numpy as np
import matplotlib.pyplot as plt
from skimage import io
from sklearn.cluster import KMeans

# 1. Load image
image = io.imread("file:///C:/Users/Microsoft/Downloads/istockphoto-2173440246-1024x1024.jpg")

# 2. Reshape image into (num_pixels, 3) for RGB
pixels = image.reshape(-1, 3)
c=12
# 3. Use KMeans to cluster colors
kmeans = KMeans(n_clusters=12 ,random_state=42)
labels = kmeans.fit_predict(pixels)

# 4. Replace pixel values with their cluster center
segmented_img = kmeans.cluster_centers_[labels].reshape(image.shape).astype(np.uint8)

# 5. Show original vs segmented
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
ax1.imshow(image)
ax1.set_title("Original Image")
ax1.axis("off")

ax2.imshow(segmented_img)
ax2.set_title(f"Segmented Image ({c} colors)")
ax2.axis("off")

plt.show()
