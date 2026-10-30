import {describe,it,expect,vi,afterEach} from 'vitest';
import {api,clock,navigation} from './lib';
afterEach(()=>vi.unstubAllGlobals());
describe('operational formatting and requests',()=>{
 it('uses London time across DST',()=>{expect(clock('2026-10-25T00:30:00Z')).toBe('01:30');expect(clock('2026-10-25T01:30:00Z')).toBe('01:30')});
 it('links to explicit navigation coordinates',()=>expect(navigation(52,-.4)).toContain('destination=52,-0.4'));
 it('does not turn rejected commits into success',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:'State changed'})}));await expect(api('/plans/x/commit','POST',{})).rejects.toThrow('State changed')});
 it('submits JSON to the same-origin proxy',async()=>{const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({trip_id:'x'})});vi.stubGlobal('fetch',fetch);expect(await api('/plans/x/commit','POST',{route_index:0})).toEqual({trip_id:'x'});expect(fetch).toHaveBeenCalledWith('/api/plans/x/commit',expect.objectContaining({method:'POST',body:'{"route_index":0}'}))});
});
