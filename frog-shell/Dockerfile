# Frog AI UI - Final Containerized Web Front-end
FROM nginx:alpine

# Copy the static web assets to the Nginx serving directory
# We only need the index.html for the web version
COPY ./index.html /usr/share/nginx/html/index.html

# Expose port 80 for the Nginx server
EXPOSE 80

# The default Nginx configuration is sufficient for this single-page app
CMD ["nginx", "-g", "daemon off;"]
