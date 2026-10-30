"""Server-side account provisioning. Password is prompted, never a command argument."""
import argparse
import getpass
from .db import factory,User,DriverRow
from .security import password_hash

def main():
    p=argparse.ArgumentParser();p.add_argument('username');p.add_argument('--role',choices=['admin','dispatcher','driver'],required=True);p.add_argument('--driver-id')
    args=p.parse_args();password=getpass.getpass('New password (12+ characters): ')
    if len(password)<12:raise SystemExit('Password too short')
    _,Session=factory()
    with Session.begin() as s:
        if args.role=='driver' and (not args.driver_id or not s.get(DriverRow,args.driver_id)):raise SystemExit('Existing --driver-id required')
        if s.get(User,args.username):raise SystemExit('Account already exists; refusing overwrite')
        s.add(User(id=args.username,password=password_hash(password),role=args.role,driver_id=args.driver_id))
    print('Account created')
if __name__=='__main__':main()
