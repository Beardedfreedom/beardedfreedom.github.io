/* Florida Freedom World private review: service worker.
   Serves the decrypted site from this browser's cache under ./app/. Nothing under app/ is ever
   fetched from the network; if the cache is empty (locked) a page request goes back to the gate. */
var CACHE='ffw-review-v1';

self.addEventListener('install',function(){ self.skipWaiting(); });
self.addEventListener('activate',function(e){ e.waitUntil(self.clients.claim()); });

function appUrl(path){ return new URL('app/'+path, self.registration.scope).href; }

self.addEventListener('message',function(e){
  var d=e.data||{}, port=e.ports&&e.ports[0];
  var reply=function(m){ if(port) port.postMessage(m); };
  var fail=function(err){ reply({ok:false,error:String(err&&err.message||err)}); };
  if(d.type==='store'){
    e.waitUntil(caches.open(CACHE).then(function(c){
      return Promise.all((d.files||[]).map(function(f){
        return c.put(appUrl(f.path), new Response(f.buf,{status:200,headers:{'Content-Type':f.type,'Cache-Control':'no-store'}}));
      }));
    }).then(function(){ reply({ok:true}); }, fail));
  }else if(d.type==='clear'){
    e.waitUntil(caches.delete(CACHE).then(function(){ reply({ok:true}); }, fail));
  }else if(d.type==='count'){
    e.waitUntil(caches.open(CACHE).then(function(c){ return c.keys(); }).then(function(k){ reply({ok:true,count:k.length}); }, fail));
  }else{
    reply({ok:true});
  }
});

self.addEventListener('fetch',function(e){
  var u=new URL(e.request.url);
  var appBase=new URL('app/', self.registration.scope);
  if(u.origin!==appBase.origin || u.pathname.indexOf(appBase.pathname)!==0) return; // not ours: normal network
  e.respondWith(caches.open(CACHE).then(function(c){
    var key=u.origin+u.pathname; if(key.slice(-1)==='/') key+='index.html';
    return c.match(key).then(function(r){
      if(!r){
        if(e.request.mode==='navigate') return Response.redirect(new URL('./?locked=1', self.registration.scope).href, 302);
        return new Response('Locked',{status:404,headers:{'Content-Type':'text/plain'}});
      }
      var range=e.request.headers.get('range');
      if(!range) return r;
      // byte ranges for <video> (Safari insists on them)
      return r.arrayBuffer().then(function(buf){
        var m=/bytes=(\d*)-(\d*)/.exec(range); var total=buf.byteLength;
        var start=m&&m[1]?parseInt(m[1],10):0; var end=m&&m[2]?Math.min(parseInt(m[2],10),total-1):total-1;
        if(start>end||start>=total) return new Response(null,{status:416,headers:{'Content-Range':'bytes */'+total}});
        var h=new Headers(r.headers); h.set('Content-Range','bytes '+start+'-'+end+'/'+total); h.set('Content-Length',String(end-start+1)); h.set('Accept-Ranges','bytes');
        return new Response(buf.slice(start,end+1),{status:206,headers:h});
      });
    });
  }));
});
