# D-OmniTwin — web-image (#408): de bestanden van de viewer (static/) en de gebouwde
# beheeromgeving (static/admin-panel), geserveerd door nginx zonder root.
#
# Generiek: geen omgevingsconfig in de image. Instellingen, sessies en data komen van de backend
# (/api); de gateway (Traefik) verdeelt de paden. Config van nginx: deploy/web/.
# Wat er in de bouwcontext komt: web.Dockerfile.dockerignore (alleen static/ en deploy/web/).
FROM nginxinc/nginx-unprivileged:1.30.5-alpine

# Voorbeeldpagina's van nginx weg; de bestanden blijven van root (alleen-lezen voor nginx)
USER root
RUN rm -f /usr/share/nginx/html/index.html /usr/share/nginx/html/50x.html
COPY deploy/web/default.conf /etc/nginx/conf.d/default.conf
COPY deploy/web/headers.conf /etc/nginx/omnitwin/headers.conf
COPY static /usr/share/nginx/html/static
USER 101

EXPOSE 8080
