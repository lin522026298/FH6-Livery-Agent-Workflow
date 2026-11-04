#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using namespace std;
int W=0,H=0,N=0;
double RES_SCALE=1;
bool inserting=false;
bool foregroundMode=false;
bool crescentSearch=false;
bool detailSearch=false;
int frozenSeedCount=0;
vector<unsigned char> foreground;
vector<int> backgroundPrefix;
struct RGB{float r=255,g=255,b=255;};
struct V{double x,y;};
struct S{int type=0;double x=0,y=0,w=10,h=10,rot=0,a=1;RGB c;};
struct Pix{int p;float v;};
struct Box{int x0,y0,x1,y1;};
vector<vector<V>> templates;
vector<V> centroids;
vector<RGB> target,canvas,pre,without;
vector<RGB> seedCanvas; vector<float> seedAlpha;
vector<float> weights,trans;
vector<float> canvasA,preA,withoutA;
vector<S> shapes;
RGB emptyPixel(int p){if(!seedCanvas.empty())return seedCanvas[p];return foregroundMode && foreground[p]?RGB{128,128,128}:RGB{};}
mt19937 rng(73461);
double rnd(){return (rng()+.5)/4294967296.;}
double norm(){static normal_distribution<double>d(0,1);return d(rng);}
double clampd(double x,double a,double b){return max(a,min(b,x));}
Box frame;
bool intersect(Box a,Box b){return a.x0<b.x1&&a.x1>b.x0&&a.y0<b.y1&&a.y1>b.y0;}
vector<V> verts(const S&s){vector<V> v;double c=cos(s.rot),t=sin(s.rot);for(auto p:templates[s.type]){double x=p.x*s.w,y=p.y*s.h;v.push_back({s.x+c*x-t*y,s.y+t*x+c*y});}return v;}
Box bounds(const S&s,int pad=0){auto v=verts(s);double x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(auto p:v){x0=min(x0,p.x);y0=min(y0,p.y);x1=max(x1,p.x);y1=max(y1,p.y);}return {max(0,int(floor(x0))-pad),max(0,int(floor(y0))-pad),min(W,int(ceil(x1))+pad),min(H,int(ceil(y1))+pad)};}
Box unite(Box a,Box b){return {min(a.x0,b.x0),min(a.y0,b.y0),max(a.x1,b.x1),max(a.y1,b.y1)};}
// Scan conversion uses the unchanged resource boundary, with four vertical
// samples and exact horizontal overlap per sample. Native SVG rendering is audited separately.
vector<Pix> raster(const S&s,Box clip=frame){
 auto vs=verts(s);Box b=bounds(s);b={max(b.x0,clip.x0),max(b.y0,clip.y0),min(b.x1,clip.x1),min(b.y1,clip.y1)};
 vector<Pix> out;if(b.x1<=b.x0||b.y1<=b.y0)return out;out.reserve((b.x1-b.x0)*(b.y1-b.y0));
 vector<float> rowStorage(W);float* row=rowStorage.data();
 for(int y=b.y0;y<b.y1;y++){
  fill(row+b.x0,row+b.x1,0);
  for(int sub=0;sub<4;sub++){
   double yy=y+(sub+.5)/4.;double xs[256];int nx=0;
   for(int j=0;j<(int)vs.size();j++){V a=vs[j],z=vs[(j+1)%vs.size()];if((a.y<=yy&&z.y>yy)||(z.y<=yy&&a.y>yy))xs[nx++]=a.x+(yy-a.y)*(z.x-a.x)/(z.y-a.y);}
   sort(xs,xs+nx);
   for(int j=0;j+1<nx;j+=2){double lo=xs[j],hi=xs[j+1];if(hi<=lo)continue;int l=max(b.x0,int(floor(lo))),r=min(b.x1-1,int(floor(hi)));
   for(int x=l;x<=r;x++)row[x]+=.25*max(0.,min(x+1.,hi)-max(double(x),lo));}
  }
  for(int x=b.x0;x<b.x1;x++)if(row[x]>0)out.push_back({y*W+x,row[x]});
 }return out;
}
void paint(vector<RGB>&im,const S&s,Box b=frame){auto *alphas=&canvasA;if(&im==&pre)alphas=&preA;else if(&im==&without)alphas=&withoutA;for(auto p:raster(s,b)){double a=p.v*s.a;auto &c=im[p.p];c.r+=a*(s.c.r-c.r);c.g+=a*(s.c.g-c.g);c.b+=a*(s.c.b-c.b);if(foregroundMode)(*alphas)[p.p]+=a*(1-(*alphas)[p.p]);}}
void render(){for(int p=0;p<N;p++){canvas[p]=emptyPixel(p);if(foregroundMode)canvasA[p]=seedAlpha.empty()?0:seedAlpha[p];}for(auto&s:shapes)paint(canvas,s);}
// Exact native-pixel row sums accelerate opaque insertion. They do not resize or
// blur the target. Fractional boundary pixels still use their actual coverage.
vector<double> pa,pr,pg,pb,pk;
void refreshPrefix(Box b){
 for(int y=b.y0;y<b.y1;y++){int z=y*(W+1);pk[z]=0;for(int x=0;x<W;x++){int p=y*W+x;auto c=canvas[p],t=target[p];double k=weights[p]*(c.r*(c.r-2*t.r)+c.g*(c.g-2*t.g)+c.b*(c.b-2*t.b));if(foregroundMode)k+=weights[p]*49152*pow(1-canvasA[p],2);pk[z+x+1]=pk[z+x]+k;}}
}
void initPrefixes(){
 if(pa.empty()){
  int n=H*(W+1);pa.resize(n);pr.resize(n);pg.resize(n);pb.resize(n);pk.resize(n);
  for(int y=0;y<H;y++){int z=y*(W+1);for(int x=0;x<W;x++){int p=y*W+x;double w=weights[p];auto t=target[p];pa[z+x+1]=pa[z+x]+w;pr[z+x+1]=pr[z+x]+w*t.r;pg[z+x+1]=pg[z+x]+w*t.g;pb[z+x+1]=pb[z+x]+w*t.b;}}
 }refreshPrefix(frame);
}
double opaqueInsertion(S&s){
 auto vs=verts(s);Box b=bounds(s);double A=0,K=0,D[3]={0,0,0};
 if(foregroundMode)for(auto v:vs)if(v.x<0||v.y<0||v.x>W||v.y>H)return -1e30;
 for(int y=b.y0;y<b.y1;y++){
  pair<int,double> events[256];int ne=0;
  auto add=[&](int l,int r,double c){l=max(0,l);r=min(W,r);if(l<r&&c>1e-12){events[ne++]={l,c};events[ne++]={r,-c};}};
  for(int sub=0;sub<4;sub++){
   double yy=y+(sub+.5)/4.;double xs[256];int nx=0;
   for(int j=0;j<(int)vs.size();j++){auto a=vs[j],z=vs[(j+1)%vs.size()];if((a.y<=yy&&z.y>yy)||(z.y<=yy&&a.y>yy))xs[nx++]=a.x+(yy-a.y)*(z.x-a.x)/(z.y-a.y);}
   sort(xs,xs+nx);
   for(int j=0;j+1<nx;j+=2){double lo=xs[j],hi=xs[j+1];int l=floor(lo),r=floor(hi);if(l==r)add(l,l+1,.25*(hi-lo));else{add(l,l+1,.25*(l+1-lo));add(l+1,r,.25);add(r,r+1,.25*(hi-r));}}
  }
  sort(events,events+ne);double cov=0;int prev=0,z=y*(W+1);
  for(int e=0;e<ne;e++){
   int x=events[e].first;
   if(cov>1e-9&&x>prev){
    if(foregroundMode && backgroundPrefix[z+x]>backgroundPrefix[z+prev])return -1e30;
    if(abs(cov-1)<1e-8){A+=pa[z+x]-pa[z+prev];D[0]+=pr[z+x]-pr[z+prev];D[1]+=pg[z+x]-pg[z+prev];D[2]+=pb[z+x]-pb[z+prev];K+=pk[z+x]-pk[z+prev];}
    else for(int xx=prev;xx<x;xx++){int p=y*W+xx;double w=weights[p],c2=cov*cov;auto c=canvas[p],t=target[p];A+=w*c2;D[0]+=w*(cov*t.r+(c2-cov)*c.r);D[1]+=w*(cov*t.g+(c2-cov)*c.g);D[2]+=w*(cov*t.b+(c2-cov)*c.b);K+=w*((2*cov-c2)*(c.r*c.r+c.g*c.g+c.b*c.b)-2*cov*(c.r*t.r+c.g*t.g+c.b*t.b));if(foregroundMode)K+=w*(2*cov-c2)*49152*pow(1-canvasA[p],2);}
   }
   cov+=events[e].second;prev=x;
  }
 }
 if(A<1e-9)return -1e30;
 s.c={float(round(clampd(D[0]/A,0,255))),float(round(clampd(D[1]/A,0,255))),float(round(clampd(D[2]/A,0,255)))};s.a=1;
 return K+2*(s.c.r*D[0]+s.c.g*D[1]+s.c.b*D[2])-A*(s.c.r*s.c.r+s.c.g*s.c.g+s.c.b*s.c.b);
}
double error(Box b=frame){double z=0;for(int y=b.y0;y<b.y1;y++)for(int x=b.x0;x<b.x1;x++){int p=y*W+x;auto c=canvas[p],t=target[p];z+=weights[p]*(pow(c.r-t.r,2)+pow(c.g-t.g,2)+pow(c.b-t.b,2));}return z;}
// In a refit context pre is the layer below the replacement, without is the full
// image with that instance removed, and trans is transmission of all upper layers.
double evaluate(S&s,bool fit=true,Box clip=frame){
 if(inserting)return opaqueInsertion(s);
 if(foregroundMode){for(auto v:verts(s))if(v.x<0||v.y<0||v.x>W||v.y>H)return -1e30;
  for(auto p:raster(s))if(p.v>1e-9&&!foreground[p.p])return -1e30;}
 double A=0,CC=0,RC=0,alphaGain=0;array<double,3>C{},R{};
 for(auto p:raster(s,clip)){int k=p.p;double cov=p.v*trans[k],q=weights[k],q2=q*cov*cov;auto b=pre[k],t=target[k],c=without[k];double bv[3]={b.r,b.g,b.b},rv[3]={t.r-c.r,t.g-c.g,t.b-c.b};A+=q2;if(foregroundMode){double da=cov*(1-preA[k]);alphaGain+=q*49152*(2*da*(1-withoutA[k])-da*da);}for(int j=0;j<3;j++){C[j]+=q2*bv[j];R[j]+=q*cov*rv[j];CC+=q2*bv[j]*bv[j];RC+=q*cov*bv[j]*rv[j];}}
 if(A<1e-9)return -1e30;
 auto gain=[&](double a,RGB c){double f[3]={c.r,c.g,c.b},fr=0,fc=0,ff=0;for(int j=0;j<3;j++){fr+=f[j]*R[j];fc+=f[j]*C[j];ff+=f[j]*f[j];}return 2*a*(fr-RC)-a*a*(A*ff-2*fc+CC)+alphaGain;};
 if(!fit)return gain(s.a,s.c);
 double best=-1e30;S win=s;
 for(double a:{1.}){
  if(a<=0)continue;RGB c{float(round(clampd((R[0]/a+C[0])/A,0,255))),float(round(clampd((R[1]/a+C[1])/A,0,255))),float(round(clampd((R[2]/a+C[2])/A,0,255)))};
  a=round(a*255)/255.;double g=gain(a,c);if(g>best){best=g;win.c=c;win.a=a;}
 }s=win;return best;
}
S mutate(S s,double scale){
 int mode=int(rnd()*9);
 if(mode==0)s.x+=norm()*max(.45,s.w*.14)*scale;
 if(mode==1)s.y+=norm()*max(.45,s.h*.14)*scale;
 if(mode==2)s.w*=exp(norm()*.28*scale);
 if(mode==3)s.h*=exp(norm()*.28*scale);
 if(mode==4)s.rot+=norm()*.2*scale;
 if(mode==5){s.x+=norm()*max(.5,s.w*.09)*scale;s.y+=norm()*max(.5,s.h*.09)*scale;}
 if(mode==6){s.w*=exp(norm()*.18*scale);s.h*=exp(norm()*.18*scale);}
 if(mode==7)s.type=crescentSearch&&rnd()<.5?7+int(rnd()*2):int(rnd()*templates.size());
 if(mode==8){s.rot+=norm()*.08*scale;s.x+=norm()*scale;s.y+=norm()*scale;}
 s.w=clampd(s.w,.5,1300*RES_SCALE);s.h=clampd(s.h,.5,1300*RES_SCALE);s.x=clampd(s.x,-200,W+200);s.y=clampd(s.y,-200,H+200);return s;
}
pair<S,double> climb(S s,int iterations,double scale=1,Box clip=frame){double best=evaluate(s,true,clip);int stale=0;for(int k=0;k<iterations;k++){S t=mutate(s,scale*(stale>35?.35:1));double v=evaluate(t,true,clip);if(v>best+.001){s=t;best=v;stale=0;}else stale++;}return {s,best};}
vector<double>cdf;double total=0;
void updateCDF(){cdf.resize(N);total=0;for(int i=0;i<N;i++){auto c=canvas[i],t=target[i];double e=weights[i]*(pow(c.r-t.r,2)+pow(c.g-t.g,2)+pow(c.b-t.b,2));if(foregroundMode)e+=weights[i]*49152*pow(1-canvasA[i],2);total+=foregroundMode&&!foreground[i]?0:e+1;cdf[i]=total;}}
int sample(){return min(N-1,int(lower_bound(cdf.begin(),cdf.end(),rnd()*total)-cdf.begin()));}
S seed(int count){int p=sample();S s;s.x=p%W+rnd()-.5;s.y=p/W+rnd()-.5;s.type=int(rnd()*templates.size());if(crescentSearch&&(s.x<W*.32||s.x>W*.58||s.y<H*.33)&&rnd()<.6)s.type=7+int(rnd()*2);double maxsize=clampd(260.*RES_SCALE/pow(1+count/110.,.65),10,260*RES_SCALE);s.w=exp(log(2)+rnd()*log(maxsize/2));s.h=exp(log(2)+rnd()*log(maxsize/2));if(rnd()<.15){s.w*=3;s.h*=3;}
 int x=p%W,y=p/W;auto lum=[&](int k){auto c=target[k];return .21*c.r+.72*c.g+.07*c.b;};double gx=lum(y*W+min(W-1,x+1))-lum(y*W+max(0,x-1)),gy=lum(min(H-1,y+1)*W+x)-lum(max(0,y-1)*W+x);s.rot=rnd()<.6?atan2(gy,gx)+1.57079632679:rnd()*6.283185307;
 if(detailSearch){
  if(s.type>=7&&rnd()<.55){s.h=30+pow(rnd(),.6)*H*.9;s.w=1+pow(rnd(),1.6)*s.h*.22;s.rot=atan2(gy,gx);}
  auto c=centroids[s.type];double xx=c.x*s.w,yy=c.y*s.h;s.x-=cos(s.rot)*xx-sin(s.rot)*yy;s.y-=sin(s.rot)*xx+cos(s.rot)*yy;
 }
 s.a=1;return s;}
void grow(int limit){
 inserting=true;initPrefixes();updateCDF();
 while((int)shapes.size()<limit){
  int n=shapes.size();if(n%16==0)updateCDF();S best;double gain=-1e30;
  int starts=detailSearch?64:(crescentSearch?24:(n<80?16:12)),its=detailSearch?240:(n<80?90:70);
  for(int j=0;j<starts;j++){auto q=climb(seed(n),its);if(q.second>gain){best=q.first;gain=q.second;}}
  auto refined=climb(best,220,.65);best=refined.first;gain=refined.second;
  if(gain<=-1e29 && foregroundMode){
   // A thin residual region may invalidate all large random starts. Retry
   // with genuinely useful small interior shapes instead of stopping early.
   for(int retry=0;retry<400;retry++){S tiny=seed(n);tiny.type=0;tiny.w=.65;tiny.h=.65;
    auto q=climb(tiny,100,.5);if(q.second>gain){best=q.first;gain=q.second;}}
  }
  if(gain<=0){cerr<<"No improving foreground candidate"<<endl;break;}
  shapes.push_back(best);paint(canvas,best);refreshPrefix(bounds(best));
  if(shapes.size()%100==0)cout<<"grow "<<shapes.size()<<" weighted-rmse "<<sqrt(error()/accumulate(weights.begin(),weights.end(),0.)/3)<<endl;
 }
}
Box prepareContext(int idx,int skip=-1){
 inserting=false;
 Box b=bounds(shapes[idx],int(18+.3*max(shapes[idx].w,shapes[idx].h)));
 if(skip>=0)b=unite(b,bounds(shapes[skip],12));
 // Whole buffers are retained; only the local patch is populated and evaluated.
 for(int y=b.y0;y<b.y1;y++)for(int x=b.x0;x<b.x1;x++){int p=y*W+x;pre[p]=emptyPixel(p);without[p]=emptyPixel(p);trans[p]=1;if(foregroundMode){preA[p]=seedAlpha.empty()?0:seedAlpha[p];withoutA[p]=0;}}
 for(int j=0;j<idx;j++)if(j!=skip&&intersect(bounds(shapes[j]),b))paint(pre,shapes[j],b);
 for(int y=b.y0;y<b.y1;y++)for(int x=b.x0;x<b.x1;x++){without[y*W+x]=pre[y*W+x];if(foregroundMode)withoutA[y*W+x]=preA[y*W+x];}
 for(int j=idx+1;j<(int)shapes.size();j++)if(j!=skip&&intersect(bounds(shapes[j]),b)){
  auto&s=shapes[j];for(auto p:raster(s,b)){double a=p.v*s.a;auto&c=without[p.p];c.r+=a*(s.c.r-c.r);c.g+=a*(s.c.g-c.g);c.b+=a*(s.c.b-c.b);trans[p.p]*=1-a;if(foregroundMode)withoutA[p.p]+=a*(1-withoutA[p.p]);}
 }return b;
}
void refit(int passes){
 // Row prefix tables are unnecessary during layer refits. Release them between
 // insertion batches so native-resolution fitting does not retain two working sets.
 vector<double>().swap(pa);vector<double>().swap(pr);vector<double>().swap(pg);vector<double>().swap(pb);vector<double>().swap(pk);vector<double>().swap(cdf);
 for(int pass=0;pass<passes;pass++){
  int improved=0,removed=0;
  for(int i=int(shapes.size())-1;i>=(foregroundMode?frozenSeedCount:1);i--){
   Box b=prepareContext(i);S old=shapes[i];double oldGain=evaluate(old,false,b);auto q=climb(old,pass?50:75,.5,b);
   // The candidate must stay within the patch used to reconstruct all occluders.
   Box bb=bounds(q.first);
   if(bb.x0<b.x0||bb.y0<b.y0||bb.x1>b.x1||bb.y1>b.y1)continue;
   if(q.second<.05){shapes.erase(shapes.begin()+i);removed++;}
   else if(q.second>oldGain+.02){shapes[i]=q.first;improved++;}
   if(i%500==0)cout<<"refit pass "<<pass+1<<" remaining "<<i<<endl;
  }
  render();cout<<"refit complete improved "<<improved<<" removed "<<removed<<" count "<<shapes.size()<<" weighted-rmse "<<sqrt(error()/accumulate(weights.begin(),weights.end(),0.)/3)<<endl;
 }
}
void reorderAndMerge(){
 int swaps=0,merges=0;
 for(int k=0;k<180;k++){
  if(shapes.size()<3)break;int i=1+int(rnd()*(shapes.size()-2)),j=i+1;
  Box a=bounds(shapes[i]),b=bounds(shapes[j]);if(!intersect(a,b))continue;Box box=unite(a,b);
  double old=error(box);swap(shapes[i],shapes[j]);
  for(int y=box.y0;y<box.y1;y++)for(int x=box.x0;x<box.x1;x++)canvas[y*W+x]=RGB{};
  for(auto&s:shapes)if(intersect(bounds(s),box))paint(canvas,s,box);
  if(error(box)<old)swaps++;else{swap(shapes[i],shapes[j]);for(int y=box.y0;y<box.y1;y++)for(int x=box.x0;x<box.x1;x++)canvas[y*W+x]=RGB{};for(auto&s:shapes)if(intersect(bounds(s),box))paint(canvas,s,box);}
 }
 for(int k=0;k<100;k++){
  if(shapes.size()<3)break;int i=1+int(rnd()*(shapes.size()-2)),j=i+1;
  auto a=shapes[i],b=shapes[j];if(!intersect(bounds(a),bounds(b)))continue;
  double dc=pow(a.c.r-b.c.r,2)+pow(a.c.g-b.c.g,2)+pow(a.c.b-b.c.b,2);if(dc>3600)continue;
  Box patch=prepareContext(i,j);double oldErr=error(patch),noErr=0;
  for(int y=patch.y0;y<patch.y1;y++)for(int x=patch.x0;x<patch.x1;x++){int p=y*W+x;auto c=without[p],t=target[p];noErr+=weights[p]*(pow(c.r-t.r,2)+pow(c.g-t.g,2)+pow(c.b-t.b,2));}
  S s=a;s.x=(a.x+b.x)/2;s.y=(a.y+b.y)/2;s.w=max(a.w,b.w)*1.25;s.h=max(a.h,b.h)*1.25;
  auto q=climb(s,180,.65,patch);Box bb=bounds(q.first);
  if(noErr-q.second<oldErr-.01&&bb.x0>=patch.x0&&bb.y0>=patch.y0&&bb.x1<=patch.x1&&bb.y1<=patch.y1){shapes[i]=q.first;shapes.erase(shapes.begin()+j);merges++;render();}
 }
 cout<<"order swaps "<<swaps<<" merges "<<merges<<endl;
}
void save(string path){ofstream f(path);f.precision(12);f<<shapes.size()<<'\n';for(auto&s:shapes)f<<s.type<<' '<<s.x<<' '<<s.y<<' '<<s.w<<' '<<s.h<<' '<<s.rot<<' '<<s.a<<' '<<s.c.r<<' '<<s.c.g<<' '<<s.c.b<<'\n';}
void recycle(int budget,int cycles,string path){
 for(int cycle=0;cycle<cycles;cycle++){
  render();double previous=error();auto backup=shapes;
  vector<pair<double,int>> scores;
  for(int i=1;i<(int)shapes.size();i++){Box b=prepareContext(i);S s=shapes[i];scores.push_back({evaluate(s,false,b),i});}
  sort(scores.begin(),scores.end());int take=int(shapes.size()*(cycle<2?.12:.07));vector<int> del;for(int j=0;j<take;j++)del.push_back(scores[j].second);sort(del.rbegin(),del.rend());for(int i:del)shapes.erase(shapes.begin()+i);
  render();grow(budget);refit(2);reorderAndMerge();render();double now=error();
  if(now>=previous){shapes=backup;render();cout<<"recycle rejected "<<cycle+1<<endl;}else cout<<"recycle accepted "<<cycle+1<<" improvement "<<100*(previous-now)/previous<<"%"<<endl;
  save(path);
 }
}
void recycleForeground(int budget,int cycles,string path){
 for(int cycle=0;cycle<cycles;cycle++){
  render();double previous=error();auto backup=shapes;
  vector<pair<double,int>> scores;
  for(int i=frozenSeedCount;i<(int)shapes.size();i++){Box b=prepareContext(i);scores.push_back({evaluate(shapes[i],false,b),i});}
  if(scores.empty())break;
  sort(scores.begin(),scores.end());int take=min(int(scores.size()),max(1,int(shapes.size()*.06)));vector<int> del;
  for(int j=0;j<take;j++)del.push_back(scores[j].second);
  sort(del.rbegin(),del.rend());for(int i:del)shapes.erase(shapes.begin()+i);
  render();grow(budget);refit(4);render();grow(budget);render();double now=error();
  if(now>=previous){shapes=backup;render();cout<<"foreground recycle rejected "<<cycle+1<<endl;}
  else cout<<"foreground recycle accepted "<<cycle+1<<" improvement "<<100*(previous-now)/previous<<"%"<<endl;
  save(path);
 }
}
int main(int argc,char**argv){
 crescentSearch=bool(ifstream("crescent-search.txt"));
 detailSearch=bool(ifstream("detail-search.txt"));
 if(argc<3){cerr<<"optimizer budget output [input] [passes]\n";return 1;}ifstream dims("dimensions.txt"); if(!(dims>>W>>H)||W<1||H<1||W>8192||H>8192){cerr<<"Invalid native dimensions";return 2;} N=W*H;RES_SCALE=max(W,H)/890.;frame={0,0,W,H};target.resize(N);canvas.resize(N);pre.resize(N);without.resize(N);weights.resize(N);trans.resize(N,1);auto start=chrono::steady_clock::now();int budget=stoi(argv[1]),passes=argc>4?stoi(argv[4]):2;if(budget<1||budget>3000)return 2;
 ifstream tf("templates.dat");int nt,nv;tf>>nt;for(int j=0;j<nt;j++){tf>>nv;vector<V>v(nv);for(auto&p:v)tf>>p.x>>p.y;templates.push_back(v);}
 ifstream("target.rgb",ios::binary).read((char*)target.data(),N*sizeof(RGB));ifstream("weights.bin",ios::binary).read((char*)weights.data(),N*sizeof(float));
 for(auto&v:templates){double a=0,cx=0,cy=0;for(int j=0;j<(int)v.size();j++){auto p=v[j],q=v[(j+1)%v.size()];double cross=p.x*q.y-q.x*p.y;a+=cross;cx+=(p.x+q.x)*cross;cy+=(p.y+q.y)*cross;}centroids.push_back({cx/(3*a),cy/(3*a)});}
 ifstream maskFile("foreground.bin",ios::binary);if(maskFile){foregroundMode=true;foreground.resize(N);maskFile.read((char*)foreground.data(),N);if(maskFile.gcount()!=N)return 2;backgroundPrefix.resize(H*(W+1));for(int y=0;y<H;y++)for(int x=0;x<W;x++)backgroundPrefix[y*(W+1)+x+1]=backgroundPrefix[y*(W+1)+x]+!foreground[y*W+x];}
 if(ifstream("base_seed.rgb")){if(!foregroundMode)return 2;seedCanvas.resize(N);seedAlpha.resize(N);ifstream sc("base_seed.rgb",ios::binary),sa("base_seed.alpha",ios::binary);sc.read((char*)seedCanvas.data(),N*sizeof(RGB));sa.read((char*)seedAlpha.data(),N*sizeof(float));if(sc.gcount()!=N*sizeof(RGB)||sa.gcount()!=N*sizeof(float))return 2;for(int i=0;i<N;i++)if(!isfinite(seedAlpha[i])||seedAlpha[i]<0||seedAlpha[i]>1)return 2;}
 if(argc>3&&string(argv[3])!="-"){ifstream f(argv[3]);int n;f>>n;shapes.resize(n);for(auto&s:shapes)f>>s.type>>s.x>>s.y>>s.w>>s.h>>s.rot>>s.a>>s.c.r>>s.c.g>>s.c.b;}
 else if(!foregroundMode){S b;b.x=W/2.;b.y=H/2.;b.w=W;b.h=H;b.c={255,255,255};shapes.push_back(b);}
 ifstream frozenFile("frozen-seed-count.txt");if(frozenFile){frozenFile>>frozenSeedCount;if(!foregroundMode||frozenSeedCount<0||frozenSeedCount>(int)shapes.size()||(int)shapes.size()>budget){cerr<<"Invalid frozen foreground seed";return 2;}}
 if(foregroundMode){canvasA.resize(N);preA.resize(N);withoutA.resize(N);render();grow(budget);save(string(argv[2])+".initial");refit(passes);render();grow(budget);render();save(argv[2]);ofstream auditRGB(string(argv[2])+".canvas.rgb",ios::binary);auditRGB.write((char*)canvas.data(),N*sizeof(RGB));ofstream auditA(string(argv[2])+".canvas.alpha",ios::binary);auditA.write((char*)canvasA.data(),N*sizeof(float));if(argc>5&&string(argv[5])!="audit")recycleForeground(budget,stoi(argv[5]),argv[2]);cout<<"DONE foreground count "<<shapes.size()<<" elapsed "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<endl;return 0;}
 if(argc>5&&string(argv[5])=="audit"){
  render();ofstream out(argv[2]);out<<"instance,weighted_squared_error_reduction\n";double low=1e30;int zero=0;
  for(int i=1;i<(int)shapes.size();i++){Box b=prepareContext(i);S s=shapes[i];double gain=evaluate(s,false,b);out<<i+1<<','<<gain<<'\n';low=min(low,gain);if(gain<=.05)zero++;}
  cout<<"contribution audit count "<<shapes.size()<<" minimum "<<low<<" negligible-or-negative "<<zero<<endl;return 0;
 }
 render();grow(budget);save(string(argv[2])+".initial");refit(passes);reorderAndMerge();grow(budget);refit(1);render();save(argv[2]);
 if(argc>5)recycle(budget,stoi(argv[5]),argv[2]);
 ofstream im(string(argv[2])+".rgb",ios::binary);im.write((char*)canvas.data(),N*sizeof(RGB));
 cout<<"DONE count "<<shapes.size()<<" elapsed "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<" weighted-rmse "<<sqrt(error()/accumulate(weights.begin(),weights.end(),0.)/3)<<endl;
}
