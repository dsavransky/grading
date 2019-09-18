function autolate(dr,duedate,outname)
%due date: YYYY-MM-DD ('2016-09-05')

if ~exist('dr','var') || isempty(dr), dr='.'; end
if ~exist('outname','var') || isempty(outname), outname='lateres'; end

duedate = datetime([duedate,' 17:00:00'],'TimeZone','America/New_York');

files = dir([dr,filesep,'*.txt']);
late = zeros(length(files),1);
netids = cell(size(files));

for j=1:length(files)
    fid = fopen([dr,filesep,files(j).name]);
    res = textscan(fid,'%s','Delimiter','\n');
    fclose(fid);
    tmp = res{1}{3};
    
    
    dat = datetime(tmp(17:end),'InputFormat',...
        'eeee, MMMM d, yyyy h:m:s a z','TimeZone','America/New_York');

    if dat > duedate
        late(j) = 1;
    end
    
    tmp = strsplit(files(j).name(1:end-2),'_');
    netids{j} = tmp{2};
end

%look for roster file
rosterfile = [dr,filesep,'Course Roster - Master.csv'];
if exist(rosterfile,'file')
    fid = fopen(rosterfile);
    roster = textscan(fid,'%s %s %s %s %s','Delimiter',',');
    fclose(fid);
    
    laststudent = find(cellfun(@isempty,roster{3}),1)-1;
    rnetids = roster{3}(2:laststudent);
    rlate = zeros(length(rnetids),1);
    
    for j = 1:length(netids)
        tmp = find(strcmp(rnetids,netids{j}));
        if isempty(tmp)
            warning('autolate:netid',['NetID not found in roster: ',netids{j}]);
            rnetids{length(rnetids)+1} = netids{j};
            rlate(length(rlate+1)) = late(j);
        else
            rlate(tmp) = late(j);
        end
    end
    
    netids = rnetids;
    late = rlate;
else
    warning('autolate:noroster','No Roster File Found');
end

T = table(netids,late);
writetable(T,[dr,filesep,outname,'.csv'])