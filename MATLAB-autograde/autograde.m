function [netids,grades] = autograde(dr,outname,resumeat)

% autograde(dr) executes all m files in the directory dr, renaming to
% 'HW?_netid' if needed (i.e., file is named in Blackboard format) and
% records scores. 
% autograde(dr,outname) prints the results to file outname in directory dr.
% if not set, a default filename (hwres) is used.
% autograde(...,resumeat) will restart grading at netid matching resumeat.
% Note that if a new grading session is started in the same folder, the
% backup will be overwritten and previous scores will be lost.


%Example:
%   %start new grading
%   autograde('sampleHw1','hw1res')
%   %resume at student cc123
%   autograde('sampleHw1','hw1res','cc123')

if ~exist('dr','var') || isempty(dr), dr='.'; end
if ~exist('outname','var') || isempty(outname), outname='hwres'; end
if ~exist('resumeat','var') || isempty(resumeat), resumeat=''; end

%define backup
bckfile = [dr,filesep,'scoresbackup.mat'];
if ~isempty(resumeat)
    if ~exist(bckfile,'file')
        error('Cannot find backup file - nothing to resume from.');
    end
    load(bckfile)
    files = dir([dr,filesep,'*.m']);
else
    %set up files
    files = dir([dr,filesep,'*.m']);
    grades = zeros(length(files),1);
    netids = cell(size(files));
    comments = cell(size(files));
end

%get screen size
sz = get(0,'ScreenSize');

caughtUp = false;
for j=1:length(files)
    %need to rename files so that MATLAB doesn't choke on the dashes
    %Blackboard sticks in.
    tmp = strsplit(files(j).name(1:end-2),'_');
    if strfind(files(j).name,'-')
        newname = [tmp{1},'_',tmp{2},'.m'];
        res = movefile([dr,filesep,files(j).name],[dr,filesep,newname]);
        if res ~= 1
            error('autograde:renameError',['Could not rename file: ',files(j).name])
        end
    else
        newname = files(j).name;
    end
    
    if ~isempty(resumeat) && ~caughtUp
        if strcmp(tmp{2},resumeat)
            caughtUp = true; 
        else
            continue
        end
    end
    
    netids{j} = tmp{2};
    disp(['Running ',newname])
    
    try
        %run the code
        comm = ['run(''',dr,filesep,newname,''')'];
        evalin('base',comm);
        shg
        
        %try to distribute figures over as much of screen as possible
        ofigs = findobj('Type','figure');
        [~,tmp] = sort(ofigs.double);
        ofigs = ofigs(tmp);
        %put first one in top corner, and then base the rest off that
        movegui(ofigs(1),'northwest')
        if length(ofigs) > 1
            fTL = get(ofigs(1),'OuterPosition');
            T = fTL(2)+fTL(4);
            L = fTL(1);
            currL = L+fTL(3)+1; %current left
            currT = T; %current top
            maxH = fTL(4);  %max height of current row
            figure(ofigs(1))
            shg
            for k=2:length(ofigs)
                fpos = get(ofigs(k),'OuterPosition');
                %move to next row if more than 5% of the fig is obscured
                if currL + fpos(3)*1.05 > sz(3)
                    currL = L;
                    currT = currT - maxH - 1;
                    maxH = fpos(4);
                end
                figure(ofigs(k))
                set(ofigs(k),'OuterPosition',...
                    [currL,max([currT - fpos(4),0]),fpos(3),fpos(4)])
                currL = currL + fpos(3) + 1;
                if fpos(4) > maxH; maxH = fpos(4); end
                shg
            end
        end
        
        %return focus to command window and get scores
        commandwindow
        disp(['Ran ',newname])
        x = [];
        while isempty(x)
            x = input('Points: ');
        end
        grades(j) = x;
        x = input('Comment: ','s');
        comments{j} = x;
    catch
        disp([newname, ' could not be run.'])
        open([dr,filesep,newname])
        commandwindow
        x = input('Points: ');
        commandwindow
        grades(j) = x;
        x = input('Comment: ','s');
        comments{j} = x;
        h = matlab.desktop.editor.getAll;
        h(end).close;
    end
    evalin('base','clear');
    close all
    fprintf('\n\n\n')
    save(bckfile,'files','netids','grades','comments')
end

for j = 1:length(files)
    %tmp = strsplit(files(j).name,'_');
    %fprintf('%10s\t%10d\n',tmp{1},grades(j))
    %netids{j} = tmp{1};
    fprintf('%10s\t%10d\t%10s\n',netids{j},grades(j),comments{j})
end

%look for roster file
rosterfile = [dr,filesep,'Course Roster - Master.csv'];
if exist(rosterfile,'file')
    fid = fopen(rosterfile);
    roster = textscan(fid,'%s %s %s %s %s','Delimiter',',');
    fclose(fid);
    
    laststudent = find(cellfun(@isempty,roster{3}),1)-1;
    rnetids = roster{3}(2:laststudent);
    rgrades = zeros(length(rnetids),1);
    rcomments = cell(size(rnetids));
    
    for j = 1:length(netids)
        tmp = find(strcmp(rnetids,netids{j}));
        if isempty(tmp)
            warning('autograde:netid',['NetID not found in roster: ',netids{j}]);
            rnetids{length(rnetids)+1} = netids{j};
            rgrades(length(rgrades+1)) = grades(j);
            rcomments{length(rcomments)+1} = comments{j};
        else
            rgrades(tmp) = grades(j);
            rcomments{tmp} = comments{j};
        end
    end
    
    netids = rnetids;
    grades = rgrades;
    comments = rcomments;
else
    warning('autograde:noroster','No Roster File Found');
end

T = table(netids,grades,comments);
writetable(T,[dr,filesep,outname,'.csv'])

end