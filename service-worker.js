self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(clients.claim());
});

self.addEventListener('push', function(event) {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'Nova atualizacao do Codex IA',
      icon: 'https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg',
      badge: 'https://i.pinimg.com/736x/aa/ed/e9/aaede9ac461d3bd6d80832a55282a33b.jpg',
      vibrate: [200, 100, 200],
      tag: 'codex-notification'
    };
    event.waitUntil(self.registration.showNotification(data.title || 'Codex IA', options));
  }
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});