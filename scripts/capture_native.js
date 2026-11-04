// Observe only this task's owned offscreen renderer. No GPU arguments changed.
const buffers=new Map(),locations=new Map(),attached=new Set(),captured=new Set();
const want=new Set(['model','has_livery','allowed_sides','use_direct_uv','direct_uv_scale']);
let getInt,resolve,uniformFloat,uniformInt,attributeInt;
function intState(name){const p=Memory.alloc(4);getInt(name,p);return p.readS32();}
function location(program,name){return locations.get(program+':'+name);}
function getUniform(program,name,n,integer=false){const l=location(program,name);if(l===undefined||l<0)return null;const p=Memory.alloc(n*4);(integer?uniformInt:uniformFloat)(program,l,p);return integer?Array.from(new Int32Array(p.readByteArray(n*4))):Array.from(new Float32Array(p.readByteArray(n*4)));}
function fn(name,ret,args){return new NativeFunction(resolve(Memory.allocUtf8String(name)),ret,args);}
function install(name,address){
 if(address.isNull()||attached.has(name+address))return;attached.add(name+address);
 if(name==='glGetUniformLocation')Interceptor.attach(address,{onEnter(args){this.program=args[0].toUInt32();this.name=args[1].readUtf8String().replace(/\[0\]$/,'');},onLeave(ret){if(want.has(this.name))locations.set(this.program+':'+this.name,ret.toInt32());}});
 if(name==='glBufferData')Interceptor.attach(address,{onEnter(args){const target=args[0].toUInt32(),size=args[1].toInt32();if(![0x8892,0x8893].includes(target)||size<=0||size>64*1024*1024||args[2].isNull())return;const binding=target===0x8892?0x8894:0x8895;const id=intState(binding);try{buffers.set(id,{target,size,data:args[2].readByteArray(size)});}catch(error){buffers.delete(id);send({kind:'skipped-unreadable-buffer',target,size,reason:String(error)});}}});
 if(name==='glDrawElements')Interceptor.attach(address,{onEnter(args){
  const program=intState(0x8B8D);if(location(program,'allowed_sides')===undefined)return;
  if(!uniformFloat){uniformFloat=fn('glGetUniformfv','void',['uint','int','pointer']);uniformInt=fn('glGetUniformiv','void',['uint','int','pointer']);attributeInt=fn('glGetVertexAttribiv','void',['uint','uint','pointer']);}
  const enabled=getUniform(program,'has_livery',1,true),allowed=getUniform(program,'allowed_sides',1,true),direct=getUniform(program,'use_direct_uv',1,true);if(!enabled||!enabled[0]||!allowed||!(allowed[0]&2047))return;
  const b=Memory.alloc(4);attributeInt(0,0x889F,b);const vbuf=b.readS32();attributeInt(0,0x8624,b);if(b.readS32()!==40)return;
  const ibuf=intState(0x8895),model=getUniform(program,'model',16),uvScale=getUniform(program,'direct_uv_scale',2);if(!buffers.has(vbuf)||!buffers.has(ibuf)){send({kind:'missing-required-mesh-buffer',vertex:vbuf,index:ibuf,allowedSides:allowed[0]});return;}
  const count=args[1].toInt32(),type=args[2].toUInt32(),off=args[3].toUInt32(),isz=type===0x1405?4:type===0x1403?2:0;if(!isz)return;
  const key=vbuf+':'+ibuf+':'+off+':'+count+':'+JSON.stringify(model)+':'+allowed[0];if(captured.has(key))return;captured.add(key);
  const v=buffers.get(vbuf),ix=buffers.get(ibuf);if(off+count*isz>ix.size)return;
  const indices=ix.data.slice(off,off+count*isz),joined=new Uint8Array(v.size+indices.byteLength);joined.set(new Uint8Array(v.data));joined.set(new Uint8Array(indices),v.size);
  send({kind:'mesh',sequence:captured.size,stride:40,vertexBytes:v.size,indexBytes:indices.byteLength,indexType:type,drawCount:count,model,uvScale,allowedSides:allowed[0],directUV:direct?direct[0]:0},joined.buffer);
 }});
}
Process.attachModuleObserver({onAdded(module){if(module.name.toLowerCase()!=='opengl32.dll')return;getInt=new NativeFunction(module.getExportByName('glGetIntegerv'),'void',['uint','pointer']);resolve=new NativeFunction(module.getExportByName('wglGetProcAddress'),'pointer',['pointer']);Interceptor.attach(module.getExportByName('wglGetProcAddress'),{onEnter(args){this.name=args[0].readUtf8String();},onLeave(ret){if(['glGetUniformLocation','glBufferData','glDrawElements'].includes(this.name))install(this.name,ret);}});install('glDrawElements',module.getExportByName('glDrawElements'));}});
send({kind:'ready',pid:Process.id,frida:Frida.version});
