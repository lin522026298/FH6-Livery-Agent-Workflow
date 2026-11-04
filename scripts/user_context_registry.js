const adv=Process.getModuleByName('advapi32.dll');
const open=new NativeFunction(adv.getExportByName('RegOpenKeyExW'),'int',['pointer','pointer','uint32','uint32','pointer']);
const query=new NativeFunction(adv.getExportByName('RegQueryValueExW'),'int',['pointer','pointer','pointer','pointer','pointer','pointer']);
const set=new NativeFunction(adv.getExportByName('RegSetValueExW'),'int',['pointer','pointer','uint32','uint32','pointer','uint32']);
const close=new NativeFunction(adv.getExportByName('RegCloseKey'),'int',['pointer']);
const path='Software\\ForzaTools\\ForzaLiveryStudio\\shapes',name='customGroups';
function handle(access){const out=Memory.alloc(8);const rc=open(ptr('0xffffffff80000001'),Memory.allocUtf16String(path),0,access,out);if(rc!==0)throw new Error('RegOpenKeyExW '+rc);return out.readPointer();}
rpc.exports={
 read(){const h=handle(0x20019);try{const typ=Memory.alloc(4),len=Memory.alloc(4);let rc=query(h,Memory.allocUtf16String(name),ptr(0),typ,ptr(0),len);if(rc!==0)throw new Error('Query size '+rc);const n=len.readU32();if(n>128*1024*1024)throw new Error('Unexpected size');const data=Memory.alloc(n);rc=query(h,Memory.allocUtf16String(name),ptr(0),typ,data,len);if(rc!==0)throw new Error('Query data '+rc);if(typ.readU32()!==1)throw new Error('Unexpected registry type '+typ.readU32());return {type:typ.readU32(),bytes:len.readU32(),text:data.readUtf16String((len.readU32()-2)/2)};}finally{close(h);}},
 write(text,expected){const current=this.read();if(current.text!==expected)throw new Error('Library changed since read; refusing write');const h=handle(0x20006);try{const p=Memory.allocUtf16String(text);const rc=set(h,Memory.allocUtf16String(name),0,1,p,(text.length+1)*2);if(rc!==0)throw new Error('RegSetValueExW '+rc);return {writtenBytes:(text.length+1)*2};}finally{close(h);}}
};
