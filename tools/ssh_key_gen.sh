ssh-keygen -t rsa -b 4096 \
  -f ~/.ssh/id_rsa_backend-service \
  -C "backend-service key" \
  -N "" && \
eval "$(ssh-agent -s)" && \
ssh-add ~/.ssh/id_rsa_backend-service && \
cat ~/.ssh/id_rsa_backend-service.pub