/*
 * This file uses mostly 4 spaces for indentation.
 * It also has some indentation with 1 space, as well as 2 spaces.
 * The purpose is to test that the algorithm pics the dominating mode.
 */

int main(int argc, char **argv)
{
    printf("Hello world!\n");
    if (argc >= 2) {
        printf("Your first argument is %s\n",
               argv[0]);
    }
}

int oops(void)
{
  this_is_wrong();
  my_bad();
}
