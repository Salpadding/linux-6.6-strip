#include <string.h>
#include <stdio.h>
#include <fnctl.h>

static int dump(int argc, char** argv) {
   if(argc < 3)  {
        fprintf(stderr, "invalid args\n");
        return 1;
   }

   int fd = open(argv[2], O_RDONLY);
   if(fd < 0) {
       fprintf(stderr, "open failed\n");
       return 1;
   }

   fstat(fd,)
}

int main(int argc, char** argv) {
    if(argc < 2) {
        fprintf(stderr, "invalid args\n");
        return 1;
    }

    if(!strcmp(argv[1], "dump")) {
        return dump() 
    }
} 
